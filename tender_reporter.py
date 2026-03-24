#!/usr/bin/env python3
"""
招投标简报工具
从北极星太阳能光伏网爬取招标采购数据并生成Markdown报告
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
from pathlib import Path
import sys
import re


class TenderReporter:
    def __init__(self):
        self.base_url = "https://guangfu.bjx.com.cn"
        self.tender_url = f"{self.base_url}/zb/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def get_tender_data(self, max_pages=3):
        """获取招标数据"""
        all_tenders = []

        for page in range(1, max_pages + 1):
            try:
                print(f"正在爬取第 {page} 页...")
                if page == 1:
                    url = self.tender_url
                else:
                    url = f"{self.tender_url}{page}/"

                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                response.encoding = 'utf-8'

                tenders = self._parse_tender_page(response.text)
                all_tenders.extend(tenders)

                print(f"第 {page} 页获取到 {len(tenders)} 条招标信息")

                # 如果这一页的数据少于预期，可能已经是最后一页了
                if len(tenders) < 20:
                    break

            except Exception as e:
                print(f"爬取第 {page} 页失败: {e}")
                break

        return all_tenders

    def _parse_tender_page(self, html_content):
        """解析招标页面"""
        soup = BeautifulSoup(html_content, 'html.parser')
        tenders = []

        # 查找招标信息列表
        # 从页面结构看，招标信息在特定的div或li标签中
        tender_items = soup.find_all('div', class_=re.compile(r'.*news.*')) or \
                      soup.find_all('li', class_=re.compile(r'.*news.*')) or \
                      soup.find_all('a', href=re.compile(r'/news/\d+/\d+\.shtml'))

        for item in tender_items:
            try:
                tender_info = self._extract_tender_info(item)
                if tender_info:
                    tenders.append(tender_info)
            except Exception as e:
                print(f"解析招标信息失败: {e}")
                continue

        # 如果上面的方法没找到，尝试另一种方式
        if not tenders:
            tenders = self._parse_alternative(html_content)

        return tenders[:50]  # 限制每页最多50条

    def _extract_tender_info(self, item):
        """从HTML元素中提取招标信息"""
        # 查找标题和链接
        title_elem = item.find('a') or item.find('h3') or item.find('h4')
        if not title_elem:
            return None

        title = title_elem.get_text(strip=True)
        if not title:
            return None

        # 获取链接
        link = title_elem.get('href')
        if link and not link.startswith('http'):
            link = self.base_url + link

        # 获取日期
        date_elem = item.find('span', class_=re.compile(r'.*date.*')) or \
                   item.find('time') or \
                   item.find('em')

        date_str = ""
        if date_elem:
            date_str = date_elem.get_text(strip=True)
        else:
            # 从标题或链接中提取日期
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', str(item))
            if date_match:
                date_str = date_match.group(1)

        # 如果没找到日期，使用当前日期
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")

        return {
            "title": title,
            "link": link or "",
            "date": date_str,
            "source": "北极星太阳能光伏网"
        }

    def _parse_alternative(self, html_content):
        """备用解析方法"""
        tenders = []

        # 使用正则表达式查找招标信息
        pattern = r'<a[^>]*href="([^"]*news/\d+/\d+\.shtml[^"]*)"[^>]*>([^<]*)</a>.*?(\d{4}-\d{2}-\d{2})'
        matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)

        for match in matches:
            link, title, date = match
            if not link.startswith('http'):
                link = self.base_url + link

            tenders.append({
                "title": title.strip(),
                "link": link,
                "date": date,
                "source": "北极星太阳能光伏网"
            })

        return tenders

    def generate_markdown_report(self, tenders):
        """生成Markdown格式的报告"""
        report_date = datetime.now().strftime("%Y年%m月%d日 %H:%M")

        markdown_content = f"""# 光伏行业招投标简报

**生成时间**: {report_date}  
**数据来源**: 北极星太阳能光伏网  
**招标信息数量**: {len(tenders)} 条

## 📋 最新招标采购信息

"""

        if not tenders:
            markdown_content += "\n*暂无招标信息*\n"
            return markdown_content

        # 按日期分组显示
        tenders_by_date = {}
        for tender in tenders:
            date = tender['date']
            if date not in tenders_by_date:
                tenders_by_date[date] = []
            tenders_by_date[date].append(tender)

        # 按日期倒序排列
        for date in sorted(tenders_by_date.keys(), reverse=True):
            day_tenders = tenders_by_date[date]

            markdown_content += f"\n### 📅 {date} ({len(day_tenders)} 条)\n\n"
            markdown_content += "| 项目名称 | 链接 | 招标单位 |\n"
            markdown_content += "|----------|------|----------|\n"

            for tender in day_tenders[:20]:  # 每日期最多显示20条
                title = tender['title'][:80] + "..." if len(tender['title']) > 80 else tender['title']
                link = f"[查看详情]({tender['link']})" if tender['link'] else "暂无链接"

                # 尝试从标题中提取招标单位
                bidder = self._extract_bidder_from_title(tender['title'])

                markdown_content += f"| {title} | {link} | {bidder} |\n"

        # 统计信息
        markdown_content += "\n## 📊 招标统计\n\n"

        # 按类型统计
        type_stats = self._analyze_tender_types(tenders)
        markdown_content += "### 招标类型分布\n\n"
        markdown_content += "| 类型 | 数量 | 占比 |\n"
        markdown_content += "|------|------|------|\n"

        total = len(tenders)
        for tender_type, count in type_stats.items():
            percentage = ".1f"
            markdown_content += f"| {tender_type} | {count} | {percentage}% |\n"

        markdown_content += "\n## 🔍 数据说明\n\n"
        markdown_content += "- 数据来源：北极星太阳能光伏网招标采购频道\n"
        markdown_content += "- 更新频率：实时爬取最新招标信息\n"
        markdown_content += "- 招标类型：包含EPC、组件采购、逆变器采购等各类光伏招标\n"
        markdown_content += "- 信息完整性：仅显示公开招标信息\n\n"

        markdown_content += "---\n\n"
        markdown_content += "*本报告由招投标简报工具自动生成*\n"

        return markdown_content

    def _extract_bidder_from_title(self, title):
        """从标题中提取招标单位"""
        # 常见的招标单位关键词
        bidders = [
            '华能', '国家电投', '中国电建', '中国能建', '中广核', '华润', '三峡',
            '大唐', '华电', '国电投', '国家能源', '中核', '中石油', '中石化',
            '隆基', '天合', '晶科', '通威', '正泰', '阳光电源', '华为', '上能'
        ]

        for bidder in bidders:
            if bidder in title:
                return bidder

        # 如果没找到特定单位，返回"其他"
        return "其他"

    def _analyze_tender_types(self, tenders):
        """分析招标类型分布"""
        type_keywords = {
            '组件采购': ['组件', '电池片', 'cell', 'module'],
            '逆变器采购': ['逆变器', 'inverter', '变流器'],
            'EPC总包': ['EPC', '总承包', '工程总包'],
            '支架采购': ['支架', 'bracket', 'support'],
            '运维服务': ['运维', '运检', '维护', 'operation'],
            '其他': []
        }

        stats = {key: 0 for key in type_keywords.keys()}

        for tender in tenders:
            title = tender['title'].lower()
            matched = False

            for tender_type, keywords in type_keywords.items():
                if tender_type == '其他':
                    continue
                if any(keyword.lower() in title for keyword in keywords):
                    stats[tender_type] += 1
                    matched = True
                    break

            if not matched:
                stats['其他'] += 1

        # 移除数量为0的类型
        return {k: v for k, v in stats.items() if v > 0}

    def save_report(self, markdown_content):
        """保存报告到文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"光伏招投标简报_{timestamp}.md"

        file_path = Path(filename)
        file_path.write_text(markdown_content, encoding='utf-8')

        print(f"报告已保存到: {filename}")
        return filename


def main():
    """主函数"""
    print("🏗️ 光伏招投标简报工具启动中...")
    print("=" * 50)

    reporter = TenderReporter()

    try:
        # 获取招标数据
        print("📡 获取招标数据...")
        tenders = reporter.get_tender_data(max_pages=3)

        # 生成Markdown报告
        print("📝 生成报告...")
        markdown_report = reporter.generate_markdown_report(tenders)

        # 保存报告
        print("💾 保存报告...")
        filename = reporter.save_report(markdown_report)

        print("=" * 50)
        print("✅ 招投标简报生成成功！")
        print(f"📄 文件名: {filename}")
        print(f"📊 共获取到 {len(tenders)} 条招标信息")

        # 显示报告预览
        print("\n📋 报告预览:")
        print("-" * 30)
        lines = markdown_report.split('\n')[:25]  # 显示前25行
        for line in lines:
            print(line)
        if len(markdown_report.split('\n')) > 25:
            print("... (更多内容请查看完整文件)")

    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()