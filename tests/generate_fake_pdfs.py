import os
import fitz  # PyMuPDF（也可用 import pymupdf）

# 确保 data/raw 目录存在（相对于当前工作目录）
os.makedirs("data/raw", exist_ok=True)

# 定义要生成的 PDF 内容（模拟真实设备手册片段）
pdf_data = [
    {
        "filename": "耐腐蚀化工泵选型手册.pdf",
        "content": [
            "耐腐蚀化工泵选型手册",
            "型号：CQB50-32-160",
            "流量范围：10 ~ 50 m³/h",
            "扬程范围：20 ~ 80 m",
            "适用介质：盐酸、硫酸、氢氧化钠溶液、次氯酸钠",
            "耐温范围：-20°C ~ 120°C",
            "材质：氟塑料（FEP）内衬，不锈钢外壳",
            "密封方式：磁力驱动（无泄漏）",
            "电机功率：5.5kW ~ 45kW",
            "适用行业：石油化工、精细化工、电镀、医药中间体",
            "选型注意事项：介质中若含有颗粒物，建议选用硬质合金轴承。"
        ]
    },
    {
        "filename": "高性能调节阀门技术规格.pdf",
        "content": [
            "高性能调节阀门技术规格书",
            "型号：V2000 系列气动薄膜调节阀",
            "公称通径：DN25 ~ DN300",
            "压力等级：PN16 / PN40 / Class150 / Class300",
            "适用介质：蒸汽、水、油品、腐蚀性流体（可选衬氟）",
            "温度范围：-40°C ~ 450°C（根据填料材质不同）",
            "阀体材质：WCB / CF8 / CF8M / 钛合金",
            "流量特性：等百分比 / 线性 / 快开",
            "泄露等级：ANSI Class IV ~ VI（软密封可达 VI 级）",
            "附件配置：电气定位器、限位开关、过滤减压阀",
            "选型建议：高压差工况建议采用套筒导向型结构，降低流体噪音。"
        ]
    },
    {
        "filename": "高效三相异步电机产品目录.pdf",
        "content": [
            "高效三相异步电机产品目录（IE3/IE4）",
            "型号：YE3-132S-4",
            "额定功率：5.5kW ~ 315kW",
            "电压等级：380V / 660V / 1140V",
            "极数：2P / 4P / 6P / 8P",
            "防护等级：IP55（标配）/ IP65（可选）",
            "绝缘等级：F 级（温升 B 级考核）",
            "冷却方式：IC411 自扇冷却",
            "安装方式：B3（卧式）/ B5（立式法兰）/ B35（立卧两用）",
            "能效标准：GB 18613-2020 二级能效（IE4）",
            "适用场景：风机、水泵、压缩机、破碎机等恒转矩或变转矩负载。",
            "选型提醒：变频场合需选用独立冷却风扇或变频专用电机。"
        ]
    }
]

def create_pdf(filepath, title, lines):
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    
    y = 50
    # 使用中文字体：china-s（简体宋体），也可用 china-ss（宋体）、china-ts（仿宋）等
    page.insert_text((50, y), title, fontsize=18, fontname="china-s")
    y += 40
    
    for line in lines:
        if y > 780:  # 换页
            page = doc.new_page(width=595, height=842)
            y = 50
        page.insert_text((50, y), line, fontsize=12, fontname="china-s")
        y += 25
    
    doc.save(filepath)
    doc.close()
    print(f"✅ 已生成：{filepath}")

if __name__ == "__main__":
    print("开始生成虚假设备 PDF 文件...")
    for item in pdf_data:
        filepath = os.path.join("data/raw", item["filename"])
        create_pdf(filepath, item["content"][0], item["content"][1:])
    print("🎉 全部生成完毕！现在 data/raw 目录下已有 3 个 PDF 文件。")