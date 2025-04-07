# TDX 数据导入 SQLite 分析文档

本文档分析了通达信(TDX)数据导入到 SQLite 数据库的源代码，重点关注 historyfinance 和 stock 相关表的数据来源和处理流程。

## TDX 数据导入到 SQLite 的主要流程

### 1. HistoryFinance 表导入流程

HistoryFinance 表用于存储历史财务数据，主要通过 `history_finance_import_sqlite` 函数导入：

```python
def history_finance_import_sqlite(connect, filename):
    file_date = filename[-12:-4]
    ret = historyfinancialreader(filename)
    cur = connect.cursor()
    cur.execute(f"delete from `HistoryFinance` where file_date={file_date}")
    cur.executemany(
        "insert into `HistoryFinance` (`file_date`, `market_code`, `report_date`, `values`) values (?,?,?,?)", ret)
    connect.commit()
    cur.close()
```

这个函数的关键点：
1. 从文件名中提取日期信息
2. 使用 `historyfinancialreader` 函数读取通达信格式的财务数据文件
3. 先删除同一日期的旧数据
4. 批量插入新数据到 HistoryFinance 表

`historyfinancialreader` 函数负责解析通达信的财务数据文件，它使用二进制格式读取，并解析出股票代码、报告日期等信息：

```python
def historyfinancialreader(filepath):
    """
    读取解析通达信目录的历史财务数据（来源: onefish, 公众号：一鱼策略）
    :param filepath: 字符串类型。传入文件路径
    :return: DataFrame格式。返回解析出的财务文件内容
    """
    import struct

    cw_file = open(filepath, 'rb')
    header_pack_format = '<1hI1H3L'
    header_size = struct.calcsize(header_pack_format)
    stock_item_size = struct.calcsize("<6s1c1L")
    data_header = cw_file.read(header_size)
    stock_header = struct.unpack(header_pack_format, data_header)
    max_count = stock_header[2]
    file_date = stock_header[1]
    report_size = stock_header[4]
    report_fields_count = int(report_size / 4)
    report_pack_format = '<{}f'.format(report_fields_count)
    results = []
    for stock_idx in range(0, max_count):
        cw_file.seek(header_size + stock_idx * struct.calcsize("<6s1c1L"))
        si = cw_file.read(stock_item_size)
        stock_item = struct.unpack("<6s1c1L", si)
        code = stock_item[0].decode("utf-8")
        foa = stock_item[2]
        cw_file.seek(foa)
        info_data = cw_file.read(struct.calcsize(report_pack_format))
        cw_info = list(struct.unpack(report_pack_format, info_data))
        report_date = int(cw_info[313])  # 财务公告日期
        report_date = 19000000 + report_date if report_date > 800000 else 20000000 + report_date
        results.append((file_date, modifiy_code(code), report_date, info_data))
    cw_file.close()
    return results
```

### 2. stkfinance 表导入流程

stkfinance 表存储公司财务信息，通过 `pytdx_import_finance_to_sqlite` 函数导入：

```python
def pytdx_import_finance_to_sqlite(db_connect, pytdx_connect, market):
    """导入公司财务信息"""
    marketid = get_marketid(db_connect, market)
    sql = "select stockid, marketid, code, valid, type from stock where marketid={} and type in {} and valid=1"\
        .format(marketid, get_a_stktype_list())

    # 获取股票列表
    cur = db_connect.cursor()
    all_list = cur.execute(sql).fetchall()
    db_connect.commit()

    records = []
    for stk in all_list:
        # 通过pytdx接口获取财务信息
        x = pytdx_connect.get_finance_info(1 if stk[1] == MARKETID.SH else 0, stk[2])
        
        # 检查数据是否已存在，避免重复导入
        if x is not None and x['code'] == stk[2]:
            cur.execute(
                "select updated_date from stkfinance where stockid={} and updated_date={}".format(
                    stk[0], x['updated_date']
                )
            )
            a = cur.fetchall()
            a = [x[0] for x in a]
            if a:
                continue
                
            # 准备财务数据记录
            records.append(
                (
                    stk[0], x['updated_date'], x['ipo_date'], x['province'], x['industry'], x['zongguben'],
                    x['liutongguben'], x['guojiagu'], x['faqirenfarengu'], x['farengu'], x['bgu'], x['hgu'],
                    x['zhigonggu'], x['zongzichan'], x['liudongzichan'], x['gudingzichan'], x['wuxingzichan'],
                    x['gudongrenshu'], x['liudongfuzhai'], x['changqifuzhai'], x['zibengongjijin'], x['jingzichan'],
                    x['zhuyingshouru'], x['zhuyinglirun'], x['yingshouzhangkuan'], x['yingyelirun'], x['touzishouyu'],
                    x['jingyingxianjinliu'], x['zongxianjinliu'], x['cunhuo'], x['lirunzonghe'], x['shuihoulirun'],
                    x['jinglirun'], x['weifenpeilirun'], x['meigujingzichan'], x['baoliu2']
                )
            )

    # 批量插入数据
    if records:
        cur.executemany(
            "INSERT INTO stkfinance(stockid, \
                                    updated_date, \
                                    ipo_date, \
                                    province, \
                                    industry, \
                                    zongguben, \
                                    liutongguben, \
                                    guojiagu, \
                                    faqirenfarengu, \
                                    farengu, \
                                    bgu, \
                                    hgu, \
                                    zhigonggu, \
                                    zongzichan, \
                                    liudongzichan, \
                                    gudingzichan, \
                                    wuxingzichan, \
                                    gudongrenshu, \
                                    liudongfuzhai, \
                                    changqifuzhai, \
                                    zibengongjijin, \
                                    jingzichan, \
                                    zhuyingshouru, \
                                    zhuyinglirun, \
                                    yingshouzhangkuan, \
                                    yingyelirun, \
                                    touzishouyu, \
                                    jingyingxianjinliu, \
                                    zongxianjinliu, \
                                    cunhuo, \
                                    lirunzonghe, \
                                    shuihoulirun, \
                                    jinglirun, \
                                    weifenpeilirun, \
                                    meigujingzichan, \
                                    baoliu2) \
                VALUES (?,?,?,?,?,?,?,?,?,?, \
                        ?,?,?,?,?,?,?,?,?,?, \
                        ?,?,?,?,?,?,?,?,?,?, \
                        ?,?,?,?,?,?)", records
        )
        db_connect.commit()
```

### 3. 数据表结构

#### HistoryFinance 表结构
```sql
CREATE TABLE `HistoryFinance` (
    `id` INTEGER,
    `file_date` INTEGER NOT NULL,  -- 文件日期
    `market_code` TEXT NOT NULL,   -- 市场代码
    `report_date` INTEGER NOT NULL, -- 报告日期
    `values` BLOB NOT NULL,         -- 财务数据二进制值
    PRIMARY KEY (`id` AUTOINCREMENT)
);
```

#### stkfinance 表结构
```sql
CREATE TABLE `stkfinance` (
    id INTEGER NOT NULL, 
    stockid INTEGER,              -- 股票ID
    `updated_date` INTEGER,       -- 更新日期
    `ipo_date` INTEGER,           -- 上市日期
    `province` INTEGER,           -- 省份
    `industry` INTEGER,           -- 行业
    `zongguben` NUMERIC,          -- 总股本(股)
    `liutongguben` NUMERIC,       -- 流通A股（股）
    `guojiagu` NUMERIC,           -- 国家股（股）
    `faqirenfarengu` NUMERIC,     -- 发起人法人股（股）
    `farengu` NUMERIC,            -- 法人股（股）
    `bgu` NUMERIC,                -- B股（股）
    `hgu` NUMERIC,                -- H股（股）
    `zhigonggu` NUMERIC,          -- 职工股（股）
    `zongzichan` NUMERIC,         -- 总资产（元）
    `liudongzichan` NUMERIC,      -- 流动资产（元）
    `gudingzichan` NUMERIC,       -- 固定资产（元）
    `wuxingzichan` NUMERIC,       -- 无形资产（元）
    `gudongrenshu` NUMERIC,       -- 股东人数
    `liudongfuzhai` NUMERIC,      -- 流动负债
    `changqifuzhai` NUMERIC,      -- 长期负债
    `zibengongjijin` NUMERIC,     -- 资本公积金
    `jingzichan` NUMERIC,         -- 净资产（元）
    `zhuyingshouru` NUMERIC,      -- 主营收入
    `zhuyinglirun` NUMERIC,       -- 主营利润
    `yingshouzhangkuan` NUMERIC,  -- 应收账款
    `yingyelirun` NUMERIC,        -- 营业利润
    `touzishouyu` NUMERIC,        -- 投资收益
    `jingyingxianjinliu` NUMERIC, -- 经营现金流
    `zongxianjinliu` NUMERIC,     -- 总现金流
    `cunhuo` NUMERIC,             -- 存货
    `lirunzonghe` NUMERIC,        -- 利润总额
    `shuihoulirun` NUMERIC,       -- 税后利润
    `jinglirun` NUMERIC,          -- 净利润
    `weifenpeilirun` NUMERIC,     -- 未分配利润
    `meigujingzichan` NUMERIC,    -- 每股净资产
    `baoliu2` NUMERIC,
    PRIMARY KEY (id), 
    FOREIGN KEY(stockid) REFERENCES "Stock" (stockid)
);
```

### 4. 数据来源

1. **TDX服务器**：通过 pytdx 库连接到通达信服务器（如示例中的 '120.76.152.87'）获取实时财务数据
2. **本地通达信文件**：通过解析本地通达信格式的财务数据文件导入历史财务数据

### 5. 数据处理流程

1. 首先创建/确认数据库结构（通过 `create_database` 函数）
2. 获取股票列表（从 stock 表）
3. 对每只股票：
   - 从 TDX 服务器获取财务数据
   - 检查数据是否已存在（避免重复导入）
   - 格式化数据并准备批量插入
4. 批量插入数据到相应的表（stkfinance 或 HistoryFinance）

这个系统设计将实时财务数据和历史财务数据分开存储，并使用索引优化查询性能。数据导入过程中有去重处理，确保数据的一致性。
