"""LangGraph PostgresSaver 历史检查点清理脚本。

背景
----
每调用一次 agent.invoke，LangGraph 就会往 PostgreSQL 写一组数据：
  - checkpoints        每个 checkpoint 一行，jsonb 里存 channel 版本引用与父指针
  - checkpoint_blobs   每个 channel 版本一份序列化后的状态（messages channel = 截至当前的完整对话）
  - checkpoint_writes  本次运行的写入
会话轮次越多，单份 messages 快照越大，累计体积呈 O(n²) 增长；
会话结束、用户不再使用后，这些行也不会自己消失。

清理策略（只提供安全的整会话删除）
----------------------------------
--days N：删除 N 天未活跃的**整个会话**，checkpoints / checkpoint_blobs /
         checkpoint_writes 三张表一起清空（等价于 saver.delete_thread）。
         活跃时间取 checkpoints.checkpoint->>'ts' 的最大值。

为什么不做"每个会话只保留最近 N 个 checkpoint"？
------------------------------------------------
LangGraph v4 的 checkpoint 是增量式状态：每个 checkpoint 记录自己更新了哪些 channel
（updated_channels）以及各 channel 的版本号，恢复状态时要沿 parent_checkpoint_id 链
回溯拼接。删掉中间的 checkpoint 会把这条链打断，**最新对话的记忆会直接丢失**
（实测：保留最近 3 个 checkpoint 后再提问，模型答不出之前说过的话）。
官方 saver.prune() 在 langgraph-checkpoint-postgres 3.1.2 里也仍是 NotImplementedError。
所以想瘦身请走两条路：
  1) 用户删除会话时联动清理（app/modules/chat_threads/service.py 的 delete）
  2) 用中间件限制单会话消息条数（SummarizationMiddleware），让单份快照体积封顶

用法
----
  python scripts/cleanup_checkpoints.py --stats
  python scripts/cleanup_checkpoints.py --dry-run --days 30
  python scripts/cleanup_checkpoints.py --days 30
  python scripts/cleanup_checkpoints.py --days 30 --vacuum
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import psycopg

# 允许直接以脚本方式运行：把项目根目录加入 sys.path，才能 import app.*
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langgraph.checkpoint.postgres import PostgresSaver  # noqa: E402

from app.core.config import settings  # noqa: E402


def list_threads(conn) -> list[tuple]:
    """列出每个 thread 的检查点数量、最后活跃时间、占用字节"""
    with conn.cursor() as cur:
        cur.execute(
            """
            select c.thread_id,
                   count(*)                                        as ckpts,
                   max((c.checkpoint->>'ts')::timestamptz)           as last_active,
                   coalesce(sum(pg_column_size(c.checkpoint)), 0)
                   + coalesce((select sum(pg_column_size(b.blob))
                                 from checkpoint_blobs b
                                where b.thread_id = c.thread_id), 0) as bytes
            from checkpoints c
            group by c.thread_id
            order by last_active
            """
        )
        return cur.fetchall()


def find_expired(conn, days: int) -> list[tuple]:
    """找出 days 天内没有新检查点的会话"""
    with conn.cursor() as cur:
        cur.execute(
            """
            select thread_id, count(*), max((checkpoint->>'ts')::timestamptz)
            from checkpoints
            group by thread_id
            having max((checkpoint->>'ts')::timestamptz) < now() - make_interval(days => %s)
            order by 3
            """,
            (days,),
        )
        return cur.fetchall()


def table_sizes(conn) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(
            """
            select c.relname,
                   c.reltuples::bigint                       as est_rows,
                   pg_size_pretty(pg_total_relation_size(c.oid)) as size,
                   pg_total_relation_size(c.oid)            as bytes
            from pg_class c
            join pg_namespace n on n.oid = c.relnamespace
            where n.nspname = 'public' and c.relname like 'checkpoint%'
            order by 4 desc
            """
        )
        return cur.fetchall()


def main() -> None:
    parser = argparse.ArgumentParser(description="清理 LangGraph 的 PG 检查点数据")
    parser.add_argument(
        "--days",
        type=int,
        help="删除 N 天未活跃的整个会话（三张表一起清）",
    )
    parser.add_argument("--stats", action="store_true", help="只打印占用统计")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划，不执行删除")
    parser.add_argument("--vacuum", action="store_true", help="清理后执行 VACUUM (ANALYZE) 回收空间")
    parser.add_argument("--limit", type=int, default=0, help="最多处理多少个会话（0=不限）")
    parser.add_argument(
        "--thread",
        action="append",
        default=[],
        help="只处理指定 thread_id（可重复传入），不传则处理全部",
    )
    args = parser.parse_args()

    if not args.days and not args.stats:
        parser.error("请指定 --days N 或 --stats")

    conninfo = settings.db.checkpoint_url
    print(f"目标库: {conninfo}")

    with psycopg.connect(conninfo, autocommit=True) as conn:
        print("\n表占用：")
        for name, est_rows, size, _ in table_sizes(conn):
            print(f"  {name:<24} 估算行数={est_rows:<8} {size}")

        print("\n各会话检查点占用：")
        for thread_id, ckpts, last_active, nbytes in list_threads(conn):
            print(
                f"  {thread_id:<40} ckpt={ckpts:<4} 最后活跃={last_active} "
                f"{nbytes / 1024:.1f} KB"
            )

        if args.days is not None:
            expired = find_expired(conn, args.days)
            if args.thread:
                expired = [t for t in expired if t[0] in set(args.thread)]
            if args.limit:
                expired = expired[: args.limit]

            print(f"\n[TTL] {args.days} 天未活跃的会话：{len(expired)} 个")
            for thread_id, ckpts, last_active in expired:
                print(f"  {thread_id:<40} ckpt={ckpts:<4} 最后活跃={last_active}")

            if expired and not args.dry_run:
                with PostgresSaver.from_conn_string(conninfo) as saver:
                    for thread_id, *_ in expired:
                        saver.delete_thread(thread_id)
                        print(f"  已删除 thread {thread_id} 的全部检查点数据")

            if args.vacuum and not args.dry_run:
                print("\n执行 VACUUM (ANALYZE) 回收空间...")
                with conn.cursor() as cur:
                    for table in ("checkpoints", "checkpoint_blobs", "checkpoint_writes"):
                        cur.execute(f"vacuum (analyze) {table}")
                print("完成")

    print("\n结束。" + ("（dry-run，未做任何删除）" if args.dry_run else ""))


if __name__ == "__main__":
    main()
