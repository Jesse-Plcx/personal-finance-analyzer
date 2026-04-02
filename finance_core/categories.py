from __future__ import annotations


def categorize_transaction(transaction: dict[str, object]) -> str:
    tx_type = str(transaction.get("type") or "").lower()
    counterparty = str(transaction.get("counterparty") or "").lower()
    combined = f"{tx_type} {counterparty}"

    food_keywords = [
        "美团", "饿了么", "肯德基", "kfc", "麦当劳", "餐", "食", "饭", "奶茶", "咖啡",
        "瑞幸", "星巴克", "外卖", "小吃", "烧烤", "火锅", "蜜雪", "古茗", "茶百道",
        "叮咚", "盒马", "生鲜", "蔬菜", "水果", "超市", "便利店", "零食", "面包",
        "蛋糕", "甜品", "饮料", "奈雪", "喜茶", "luckin", "必胜客", "海底捞",
        "mcdonald", "全家", "7-eleven", "罗森", "永辉", "大润发", "华润万家",
        "沃尔玛", "家乐福", "冰淇淋", "快餐", "食品", "糕点", "粥", "面馆", "寿司",
        "披萨", "烤肉", "串串", "鸡排", "汉堡", "炸鸡", "牛排", "水饺", "包子",
        "馒头", "豆浆", "早餐", "午餐", "晚餐", "夜宵", "速食", "方便面", "酸奶",
        "牛奶",
    ]
    transport_keywords = [
        "滴滴", "出租", "公交", "地铁", "高铁", "火车", "12306", "航空", "机票",
        "飞机", "打车", "铁路", "uber", "哈啰", "青桔", "共享", "单车", "加油",
        "停车", "高速", "通行费", "etc", "出行", "携程", "去哪儿", "飞猪", "同程",
        "途牛", "交通", "汽车票", "船票", "摩托", "骑行",
    ]
    shopping_keywords = [
        "淘宝", "天猫", "京东", "拼多多", "苏宁", "唯品会", "当当", "网购", "商城",
        "旗舰店", "购物", "买", "亚马逊", "小米", "华为", "apple", "数码", "电子",
        "手机", "电脑", "耳机", "充电", "配件", "积木", "乐拼", "玩具", "礼物",
        "衣服", "鞋", "包", "服装", "潮流", "时尚", "品牌", "闲鱼", "二手",
        "得物", "抖音商城", "快手", "business1000", "专营店",
    ]
    entertainment_keywords = [
        "游戏", "充值", "腾讯", "qq", "网易", "steam", "视频", "会员", "电影",
        "音乐", "直播", "打赏", "娱乐", "剧", "b站", "bilibili", "爱奇艺", "优酷",
        "芒果", "抖音", "快手", "spotify", "netflix", "apple music", "网游",
        "手游", "epic", "playstation", "xbox", "票务", "门票", "演出", "演唱会",
        "展览", "景点", "旅游", "酒店", "民宿", "住宿",
    ]
    education_keywords = [
        "学费", "教育", "培训", "课程", "学校", "书", "文具", "教材", "考试",
        "报名", "学习", "网课", "慕课", "知乎", "得到", "樊登", "晨光", "笔",
        "本子", "橡皮", "书包", "开学",
    ]
    transfer_keywords = ["转账", "红包", "零钱", "提现", "充值余额", "还款"]
    comm_keywords = ["话费", "流量", "通讯", "移动", "联通", "电信", "宽带", "手机号"]
    life_keywords = [
        "水电", "电费", "水费", "燃气", "物业", "房租", "租金", "押金", "医院",
        "药", "诊所", "体检", "保险", "社保", "公积金", "理发", "洗衣", "快递",
        "邮费", "运费", "寄件", "顺丰", "中通", "圆通", "申通", "韵达", "极兔",
        "鲜花",
    ]
    social_keywords = ["微信红包", "发给", "红包"]

    for keyword in food_keywords:
        if keyword in combined:
            return "餐饮美食"
    for keyword in transport_keywords:
        if keyword in combined:
            return "交通出行"
    for keyword in entertainment_keywords:
        if keyword in combined:
            return "休闲娱乐"
    for keyword in education_keywords:
        if keyword in combined:
            return "教育学习"
    for keyword in comm_keywords:
        if keyword in combined:
            return "通讯话费"
    for keyword in life_keywords:
        if keyword in combined:
            return "生活服务"
    for keyword in social_keywords:
        if keyword in combined:
            return "社交红包"
    for keyword in shopping_keywords:
        if keyword in combined:
            return "购物消费"
    for keyword in transfer_keywords:
        if keyword in combined:
            return "转账往来"
    return "其他"
