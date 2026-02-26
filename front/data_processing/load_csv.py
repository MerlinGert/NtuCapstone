import csv
import json
import os
import argparse
from collections import defaultdict, Counter


def process_csv(input_path: str, output_dir: str, sample_rows: int = 0, sample_max_bytes: int = 0, top_pairs: int = 20):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    os.makedirs(output_dir, exist_ok=True)

    total_rows = 0
    pairs_counter = Counter()
    dates_set = set()
    date_min = None
    date_max = None

    # pair-day aggregation limited to top pairs later to avoid huge JSON
    agg_pair_day = defaultdict(lambda: defaultdict(lambda: {"count": 0, "amount_usd_sum": 0.0}))

    # optional sample writer
    sample_writer = None
    sample_bytes = 0
    sample_path = os.path.join(output_dir, "ACT-partial.csv")
    columns_examples = {}

    with open(input_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        sample_fieldnames = reader.fieldnames
        if sample_rows > 0 or sample_max_bytes > 0:
            sample_writer = csv.DictWriter(open(sample_path, "w", newline="", encoding="utf-8"), fieldnames=sample_fieldnames)
            sample_writer.writeheader()

        for row in reader:
            total_rows += 1
            pair = row.get("token_pair", "").strip()
            date = row.get("block_date", "").strip()
            amount_usd_str = row.get("amount_usd", "").strip()
            try:
                amount_usd = float(amount_usd_str) if amount_usd_str else 0.0
            except ValueError:
                amount_usd = 0.0

            pairs_counter[pair] += 1
            if date:
                dates_set.add(date)
                if date_min is None or date < date_min:
                    date_min = date
                if date_max is None or date > date_max:
                    date_max = date

            # aggregate per pair per day
            if pair and date:
                agg = agg_pair_day[pair][date]
                agg["count"] += 1
                agg["amount_usd_sum"] += amount_usd

            # write sample if configured
            if sample_writer:
                if sample_rows and total_rows <= sample_rows:
                    sample_writer.writerow(row)
                    sample_bytes += sum(len(str(v)) for v in row.values()) + len(sample_fieldnames)  # rough
                elif sample_max_bytes and sample_bytes < sample_max_bytes:
                    sample_writer.writerow(row)
                    sample_bytes += sum(len(str(v)) for v in row.values()) + len(sample_fieldnames)

            for k, v in row.items():
                if k not in columns_examples and v:
                    columns_examples[k] = v

    # build overview
    top_pairs_list = pairs_counter.most_common(top_pairs)
    overview = {
        "rows": total_rows,
        "pairs_count": len(pairs_counter),
        "dates_count": len(dates_set),
        "date_min": date_min,
        "date_max": date_max,
        "top_pairs": [{"token_pair": p, "count": c} for p, c in top_pairs_list],
    }

    # limit aggregation to top pairs for JSON size
    limited_agg = {}
    for p, _ in top_pairs_list:
        days = agg_pair_day.get(p, {})
        limited_agg[p] = {d: v for d, v in sorted(days.items())}

    # write outputs
    overview_path = os.path.join(output_dir, "overview.json")
    agg_path = os.path.join(output_dir, "agg_pair_day.json")
    with open(overview_path, "w", encoding="utf-8") as fo:
        json.dump(overview, fo, ensure_ascii=False, separators=(",", ":"))
    with open(agg_path, "w", encoding="utf-8") as fa:
        json.dump(limited_agg, fa, ensure_ascii=False, separators=(",", ":"))

    column_desc_map = {
        "blockchain": {"type": "string", "desc": "区块链名称"},
        "project": {"type": "string", "desc": "协议或项目名称"},
        "version": {"type": "number", "desc": "协议版本号"},
        "version_name": {"type": "string", "desc": "协议版本名"},
        "block_month": {"type": "string", "desc": "月份维度"},
        "block_date": {"type": "string", "desc": "交易日期"},
        "block_time": {"type": "string", "desc": "交易时间戳"},
        "block_slot": {"type": "number", "desc": "区块或插槽编号"},
        "trade_source": {"type": "string", "desc": "交易来源或聚合器"},
        "token_bought_symbol": {"type": "string", "desc": "买入代币符号"},
        "token_sold_symbol": {"type": "string", "desc": "卖出代币符号"},
        "token_pair": {"type": "string", "desc": "交易对"},
        "token_bought_amount": {"type": "number", "desc": "买入代币数量"},
        "token_sold_amount": {"type": "number", "desc": "卖出代币数量"},
        "token_bought_amount_raw": {"type": "integer", "desc": "买入代币原始最小单位数量"},
        "token_sold_amount_raw": {"type": "integer", "desc": "卖出代币原始最小单位数量"},
        "amount_usd": {"type": "number", "desc": "交易金额折美元"},
        "fee_tier": {"type": "number", "desc": "手续费档位比例"},
        "fee_usd": {"type": "number", "desc": "手续费折美元"},
        "token_bought_mint_address": {"type": "string", "desc": "买入代币 mint 地址"},
        "token_sold_mint_address": {"type": "string", "desc": "卖出代币 mint 地址"},
        "token_bought_vault": {"type": "string", "desc": "买入代币金库地址"},
        "token_sold_vault": {"type": "string", "desc": "卖出代币金库地址"},
        "project_program_id": {"type": "string", "desc": "协议程序 ID"},
        "project_main_id": {"type": "string", "desc": "协议主对象/池 ID"},
        "trader_id": {"type": "string", "desc": "交易用户或账户 ID"},
        "tx_id": {"type": "string", "desc": "交易签名或哈希"},
        "outer_instruction_index": {"type": "integer", "desc": "外层指令索引"},
        "inner_instruction_index": {"type": "integer", "desc": "内层指令索引"},
        "tx_index": {"type": "integer", "desc": "数据集中的交易序号"},
    }

    columns_meta = []
    for name in sample_fieldnames:
        base = column_desc_map.get(name, {"type": "string", "desc": ""})
        example = columns_examples.get(name, "")
        columns_meta.append({"name": name, "type": base["type"], "desc": base["desc"], "example": example})

    columns_meta_path = os.path.join(output_dir, "columns_meta.json")
    with open(columns_meta_path, "w", encoding="utf-8") as fm:
        json.dump({"columns": columns_meta}, fm, ensure_ascii=False, separators=(",", ":"))

    outputs = {
        "overview_json": overview_path,
        "agg_json": agg_path,
        "partial_csv": sample_path if sample_writer else None,
        "columns_meta_json": columns_meta_path,
    }
    return outputs


def process_transfers_csv(input_path: str, output_dir: str, top_n: int = 20):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    os.makedirs(output_dir, exist_ok=True)

    total_rows = 0
    actions_counter = Counter()
    symbols_counter = Counter()
    from_owner_counter = Counter()
    to_owner_counter = Counter()
    edge_counter = Counter()
    from_owner_amount = defaultdict(float)
    to_owner_amount = defaultdict(float)
    edge_amount = defaultdict(float)
    unique_days = set()
    date_min = None
    date_max = None
    total_amount = 0.0
    total_amount_usd = 0.0

    columns_examples = {}
    fieldnames = []

    def _pfloat(v: str) -> float:
        try:
            return float(v) if v is not None and v != "" else 0.0
        except Exception:
            return 0.0

    with open(input_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for row in reader:
            total_rows += 1
            for k, v in row.items():
                if k not in columns_examples and v:
                    columns_examples[k] = v

            action = (row.get("action") or "").strip()
            symbol = (row.get("symbol") or "").strip()
            from_owner = (row.get("from_owner") or "").strip()
            to_owner = (row.get("to_owner") or "").strip()
            block_date = (row.get("block_date") or "").strip()
            amt = _pfloat((row.get("amount_display") or row.get("amount") or "").strip())
            usd = _pfloat((row.get("amount_usd") or "").strip())

            if action:
                actions_counter[action] += 1
            if symbol:
                symbols_counter[symbol] += 1
            if from_owner:
                from_owner_counter[from_owner] += 1
                from_owner_amount[from_owner] += usd
            if to_owner:
                to_owner_counter[to_owner] += 1
                to_owner_amount[to_owner] += usd
            if from_owner and to_owner:
                edge_key = (from_owner, to_owner)
                edge_counter[edge_key] += 1
                edge_amount[edge_key] += usd
            if block_date:
                unique_days.add(block_date)
                if date_min is None or block_date < date_min:
                    date_min = block_date
                if date_max is None or block_date > date_max:
                    date_max = block_date

            total_amount += amt
            total_amount_usd += usd

    top_from = []
    for owner, cnt in from_owner_counter.most_common(top_n):
        top_from.append({"owner": owner, "count": cnt, "amount_usd_sum": round(from_owner_amount[owner], 6)})
    top_to = []
    for owner, cnt in to_owner_counter.most_common(top_n):
        top_to.append({"owner": owner, "count": cnt, "amount_usd_sum": round(to_owner_amount[owner], 6)})
    top_edges = []
    for (fo, to), cnt in edge_counter.most_common(top_n):
        top_edges.append({"from_owner": fo, "to_owner": to, "count": cnt, "amount_usd_sum": round(edge_amount[(fo, to)], 6)})

    overview = {
        "rows": total_rows,
        "days_count": len(unique_days),
        "date_min": date_min,
        "date_max": date_max,
        "total_amount": round(total_amount, 6),
        "total_amount_usd": round(total_amount_usd, 6),
        "actions": dict(actions_counter),
        "symbols": dict(symbols_counter),
        "top_from_owners": top_from,
        "top_to_owners": top_to,
        "top_edges": top_edges,
    }

    transfers_overview_path = os.path.join(output_dir, "transfers_overview.json")
    with open(transfers_overview_path, "w", encoding="utf-8") as fo:
        json.dump(overview, fo, ensure_ascii=False, separators=(",", ":"))

    column_desc_map = {
        "block_time": {"type": "string", "desc": "区块时间（UTC）"},
        "action": {"type": "string", "desc": "动作类型（如：transfer/approve 等）"},
        "amount": {"type": "number", "desc": "原始数量（最小单位）"},
        "from_token_account": {"type": "string", "desc": "来源 token 账户"},
        "to_token_account": {"type": "string", "desc": "目标 token 账户"},
        "token_mint_address": {"type": "string", "desc": "代币 mint 地址"},
        "symbol": {"type": "string", "desc": "代币符号"},
        "amount_display": {"type": "number", "desc": "按可读精度换算后的数量"},
        "amount_usd": {"type": "number", "desc": "金额折美元"},
        "from_owner": {"type": "string", "desc": "来源账户 owner（可能为用户/程序/池）"},
        "to_owner": {"type": "string", "desc": "目标账户 owner（可能为用户/程序/池）"},
        "token_version": {"type": "string", "desc": "代币版本/变体"},
        "tx_id": {"type": "string", "desc": "交易哈希/签名"},
        "tx_signer": {"type": "string", "desc": "交易签名者"},
        "outer_executing_account": {"type": "string", "desc": "外层执行账户（程序/合约）"},
        "block_date": {"type": "string", "desc": "日期"},
        "block_slot": {"type": "number", "desc": "区块/插槽编号"},
        "tx_index": {"type": "integer", "desc": "交易序号"},
        "outer_instruction_index": {"type": "integer", "desc": "外层指令序号"},
        "inner_instruction_index": {"type": "integer", "desc": "内层指令序号"},
        "unique_instruction_key": {"type": "string", "desc": "唯一指令键"},
    }
    columns_meta = []
    for name in fieldnames:
        base = column_desc_map.get(name, {"type": "string", "desc": ""})
        example = columns_examples.get(name, "")
        columns_meta.append({"name": name, "type": base["type"], "desc": base["desc"], "example": example})
    transfers_columns_meta_path = os.path.join(output_dir, "transfers_columns_meta.json")
    with open(transfers_columns_meta_path, "w", encoding="utf-8") as fm:
        json.dump({"columns": columns_meta}, fm, ensure_ascii=False, separators=(",", ":"))

    return {
        "transfers_overview": transfers_overview_path,
        "transfers_columns_meta": transfers_columns_meta_path,
    }


def main():
    parser = argparse.ArgumentParser(description="Stream load large CSV and produce summarized JSON for frontend.")
    parser.add_argument("--mode", choices=["trades", "transfers"], default="trades", help="Processing mode")
    parser.add_argument("--input", default="public/ACT-24-11-10.csv", help="Input CSV path")
    parser.add_argument("--output-dir", default="public/processed", help="Directory to write outputs")
    parser.add_argument("--sample-rows", type=int, default=0, help="Write first N rows to partial CSV")
    parser.add_argument("--sample-max-bytes", type=int, default=50_000_000, help="Max bytes for partial CSV")
    parser.add_argument("--top-pairs", type=int, default=20, help="Number of top pairs to aggregate per day")
    parser.add_argument("--top-n", type=int, default=20, help="Top N list size for transfers mode")
    args = parser.parse_args()

    if args.mode == "trades":
        outputs = process_csv(
            input_path=args.input,
            output_dir=args.output_dir,
            sample_rows=args.sample_rows,
            sample_max_bytes=args.sample_max_bytes,
            top_pairs=args.top_pairs,
        )
    else:
        outputs = process_transfers_csv(
            input_path=args.input,
            output_dir=args.output_dir,
            top_n=args.top_n,
        )
    print(json.dumps(outputs, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
