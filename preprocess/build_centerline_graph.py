import argparse
import os
from typing import List

from centerline_graph import build_weighted_graph_from_curves, iter_curve_files, save_json_vessel_net, save_pickle


def _parse_args() -> argparse.Namespace:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=os.path.join(base_dir, "source", "mrk"),
        help="目录或单个 .mrk.json 文件路径",
    )
    parser.add_argument(
        "--merge-tol",
        type=float,
        default=0.01,
        help="节点合并容差（与文件坐标单位一致，默认 mm）",
    )
    parser.add_argument(
        "--out-pkl",
        default=os.path.join(base_dir, "source", "graphs", "centerline_vessel_net.pkl"),
        help="pickle 输出路径（WeightedAdjacency）",
    )
    parser.add_argument(
        "--out-json",
        default="",
        help="可选：JSON 输出路径（key 会被序列化为字符串）",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    curve_paths: List[str] = iter_curve_files(args.input)
    vessel_net = build_weighted_graph_from_curves(curve_paths, merge_tol=args.merge_tol, undirected=True)

    nodes = len(vessel_net)
    edges = sum(len(v) for v in vessel_net.values())
    print(f"curves={len(curve_paths)} nodes={nodes} directed_edges={edges} merge_tol={args.merge_tol}")

    out_pkl = save_pickle(vessel_net, args.out_pkl)
    print(f"saved_pickle={out_pkl}")

    if args.out_json:
        out_json = save_json_vessel_net(vessel_net, args.out_json)
        print(f"saved_json={out_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
