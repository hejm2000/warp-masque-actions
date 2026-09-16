#!/usr/bin/env python3
"""从 W2 provider 文件（14 个 198.2/199.2 稳定节点）生成自包含的完整 mihomo 配置，
供 v2rayN 作为「Clash/mihomo 完整配置」订阅导入。

v2rayN 的 ClashFmt 会识别含 rules/proxies/-port 的完整配置，自动加载到它捆绑的
mihomo 核心。masque 是 usque 自研协议（QUIC/HTTP3 + ECDSA 客户端证书），v2rayN
的三大核心里只有 mihomo 支持 type: masque，所以必须走 mihomo 核心，不能硬套
wireguard:// 或 vless:// 链接。

本配置完全自包含：
- 节点内联（不依赖外部 provider 拉取）
- 规则只用 mihomo 内置（GEOIP / DOMAIN-SUFFIX / MATCH），无外部 rule-provider
- 不依赖外网 rule 下载，冷启动即可用

用法: python3 gen_v2rayn_config.py <w2-provider.yaml> <输出文件>
"""
import sys


def extract_proxies(text):
    """从 w2-provider.yaml 抽出 proxies 块原文（保留节点字段原样）。"""
    lines = text.splitlines()
    out = []
    in_proxies = False
    for ln in lines:
        if ln.startswith("proxies:"):
            in_proxies = True
            continue
        if in_proxies:
            # 下一个顶层 key（无缩进、以冒号结尾）说明 proxies 块结束
            if ln and not ln[0].isspace() and not ln.startswith("#"):
                break
            out.append(ln)
    # 去掉末尾空行
    while out and not out[-1].strip():
        out.pop()
    return out


def build(proxies_lines):
    ind = lambda lst, n=6: "\n".join(" " * n + f"- {x}" for x in lst)

    # 节点名列表（从 proxies 块里提取）
    names = []
    for ln in proxies_lines:
        s = ln.strip()
        if s.startswith("- name:"):
            names.append(s[len("- name:"):].strip())

    groups = [
        "🚀 节点选择",
        "♻️ 自动选择",
        "🔄 故障转移",
        "☑️ 手动切换",
        "🎯 全球直连",
    ]

    return f"""# WARP MASQUE - v2rayN 订阅配置（14 个 198.2/199.2 稳定节点）
# 由 GitHub Actions 自动生成（warp-masque.yml），请勿手工编辑
#
# 用法：v2rayN → 导入订阅 → 填本文件 raw URL → 自动识别为 mihomo 配置
# 协议：type: masque（usque 自研，QUIC/HTTP3 + ECDSA 客户端证书，需 mihomo 核心）

mixed-port: 7890
allow-lan: false
mode: rule
log-level: info
ipv6: true
unified-delay: true
tcp-concurrent: true
find-process-mode: 'off'
external-controller: 127.0.0.1:9090

profile:
  store-selected: true

sniffer:
  enable: true
  sniff:
    HTTP:
      ports: [80, 8080-8880]
      override-destination: true
    TLS:
      ports: [443, 8443]
    QUIC:
      ports: [443, 8443]
  skip-domain:
    - '+.push.apple.com'
    - '+.apple.com'

dns:
  enable: true
  listen: 127.0.0.1:1053
  ipv6: true
  enhanced-mode: fake-ip
  fake-ip-range: 198.18.0.1/16
  fake-ip-filter:
    - '+.lan'
    - '+.local'
    - '*.msftconnecttest.com'
    - '*.msftncsi.com'
  default-nameserver:
    - 223.5.5.5
    - 119.29.29.29
  nameserver:
    - https://223.5.5.5/dns-query
    - https://1.12.12.12/dns-query
  proxy-server-nameserver:
    - https://223.5.5.5/dns-query
  nameserver-policy:
    'geosite:cn,private':
      - https://223.5.5.5/dns-query
      - https://1.12.12.12/dns-query
    'geosite:geolocation-!cn':
      - https://1.1.1.1/dns-query
      - https://8.8.8.8/dns-query

proxies:
{chr(10).join(proxies_lines)}

proxy-groups:
  - name: 🚀 节点选择
    type: select
    proxies:
      - ♻️ 自动选择
      - 🔄 故障转移
      - ☑️ 手动切换
      - DIRECT

  - name: ☑️ 手动切换
    type: select
    proxies:
{ind(names)}

  - name: ♻️ 自动选择
    type: url-test
    url: http://www.gstatic.com/generate_204
    interval: 300
    tolerance: 50
    lazy: false
    proxies:
{ind(names)}

  - name: 🔄 故障转移
    type: fallback
    url: http://www.gstatic.com/generate_204
    interval: 180
    proxies:
{ind(names)}

  - name: 🎯 全球直连
    type: select
    proxies:
      - DIRECT
      - 🚀 节点选择
      - ♻️ 自动选择

  - name: 🐟 漏网之鱼
    type: select
    proxies:
      - 🚀 节点选择
      - 🎯 全球直连

rules:
  - GEOIP,LAN,🎯 全球直连,no-resolve
  - GEOIP,CN,🎯 全球直连
  - MATCH,🐟 漏网之鱼
"""


def main():
    if len(sys.argv) < 3:
        print("用法: gen_v2rayn_config.py <w2-provider.yaml> <输出文件>", file=sys.stderr)
        sys.exit(1)
    src, out = sys.argv[1], sys.argv[2]
    text = open(src).read()
    proxies = extract_proxies(text)
    if not proxies:
        sys.exit("未能从源文件抽出 proxies 块")
    # 去掉 proxies 行本身（extract 保留的是节点条目，不含 "proxies:" 头）
    cfg = build(proxies)
    with open(out, "w") as f:
        f.write(cfg)
    # 节点数
    n = cfg.count("type: masque")
    print(f"已生成 {out}（{n} 个 masque 节点）")


if __name__ == "__main__":
    main()
