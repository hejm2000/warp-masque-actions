#!/usr/bin/env python3
"""从 gen_masque.py 生成的完整配置里抽出 198.2/199.2 段的 14 个稳定节点，
生成 W2 provider 文件（只有 proxies: 块，供 mihomo type: http 拉取）。

用法: python3 gen_w2_provider.py <生成的完整配置> <输出文件>
"""
import re
import sys

# 2026-09-16 全量 57 节点实测：198.2/199.2 段大流量（10MB 下载）全通，
# 198.1/199.1/WARP6(103/104)/官方域名段小请求能通但大流量挂。
WHITELIST = {
    "WARP-198.2-443", "WARP-198.2-500", "WARP-198.2-1701", "WARP-198.2-4500",
    "WARP-198.2-4443", "WARP-198.2-8443", "WARP-198.2-8095",
    "WARP-199.2-443", "WARP-199.2-500", "WARP-199.2-1701", "WARP-199.2-4500",
    "WARP-199.2-4443", "WARP-199.2-8443", "WARP-199.2-8095",
}

BLOCK = re.compile(r"^  - name: (.+?)\n(.*?)(?=^  - name: |\Z)", re.M | re.S)


def main():
    if len(sys.argv) < 3:
        print("用法: gen_w2_provider.py <完整配置> <输出文件>", file=sys.stderr)
        sys.exit(1)
    src, out = sys.argv[1], sys.argv[2]
    text = open(src).read()

    found = []
    for m in BLOCK.finditer(text):
        if m.group(1) in WHITELIST:
            found.append("  - name: " + m.group(1) + "\n" + m.group(2).rstrip())

    missing = WHITELIST - {m.group(1) for m in BLOCK.finditer(text)}
    if missing:
        sys.exit(f"生成配置里缺少白名单节点: {sorted(missing)}")
    if len(found) != len(WHITELIST):
        sys.exit(f"抽出 {len(found)} 个节点，预期 {len(WHITELIST)}")

    header = (
        "# WARP MASQUE 可用节点子集（198.2/199.2 段，大流量实测通过）\n"
        "# 由 GitHub Actions 自动生成（warp-masque.yml），请勿手工编辑\n"
    )
    with open(out, "w") as f:
        f.write(header + "proxies:\n" + "\n\n".join(found) + "\n")
    print(f"已生成 {out}（{len(found)} 个节点）")


if __name__ == "__main__":
    main()
