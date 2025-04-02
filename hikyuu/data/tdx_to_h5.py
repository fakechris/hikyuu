# coding:utf-8
#
# The MIT License (MIT)
#
# Copyright (c) 2010-2019 fasiondog/hikyuu
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os.path
import struct
import sqlite3
import datetime
import math
import sys

import tables as tb

from io import SEEK_END, SEEK_SET

from hikyuu.data.common import get_stktype_list, MARKETID
from hikyuu.data.common_sqlite3 import (
    create_database, get_marketid, get_codepre_list, update_last_date
)
from hikyuu.data.common_h5 import (
    H5Record, H5Index, open_h5file, get_h5table, update_hdf5_extern_data
)
from hikyuu.data.weight_to_sqlite import qianlong_import_weight


def ProgressBar(cur, total):
    percent = '{:.0%}'.format(cur / total)
    sys.stdout.write('\r')
    sys.stdout.write("[%-50s] %s" % ('=' * int(math.floor(cur * 50 / total)), percent))
    sys.stdout.flush()


def tdx_import_stock_name_from_file(connect, filename, market, quotations=None):
    """更新每只股票的名称、当前是否有效性、起始日期及结束日期
        如果导入的代码表中不存在对应的代码，则认为该股已失效

        :param connect: sqlite3实例
        :param filename: 代码表文件名
        :param market: 'SH' | 'SZ'
        :param quotations: 待导入的行情类别列表，空为导入全部 'stock' | 'fund' | 'bond' | None
    """
    cur = connect.cursor()

    newStockDict = {}
    with open(filename, 'rb') as f:
        data = f.read(50)
        data = f.read(314)
        while data:
            a = struct.unpack('6s 17s 8s 283s', data)
            try:
                stockcode = a[0].decode()
                stockname = a[2].decode(encoding='gbk').encode('utf8')
                pos = stockname.find(0x00)
                if pos >= 0:
                    stockname = stockname[:pos]
                newStockDict[stockcode] = stockname.decode(encoding='utf8').strip()
            except:
                pass
            data = f.read(314)

    a = cur.execute("select marketid from market where market = '%s'" % market.upper())
    marketid = [i for i in a]
    marketid = marketid[0][0]

    stktype_list = get_stktype_list(quotations)
    a = cur.execute(
        "select stockid, code, name, valid from stock where marketid={} and type in {}".format(
            marketid, stktype_list
        )
    )
    a = a.fetchall()
    oldStockDict = {}
    for oldstock in a:
        oldstockid, oldcode, oldname, oldvalid = oldstock[0], oldstock[1], oldstock[2], int(
            oldstock[3]
        )
        oldStockDict[oldcode] = oldstockid

        # 新的代码表中无此股票，则置为无效
        if (oldvalid == 1) and (oldcode not in newStockDict):
            cur.execute("update stock set valid=0 where stockid=%i" % oldstockid)

        # 股票名称发生变化，更新股票名称;如果原无效，则置为有效
        if oldcode in newStockDict:
            if oldname != newStockDict[oldcode]:
                cur.execute(
                    "update stock set name='%s' where stockid=%i" %
                    (newStockDict[oldcode], oldstockid)
                )
            if oldvalid == 0:
                cur.execute(
                    "update stock set valid=1, endDate=99999999 where stockid=%i" % oldstockid
                )

    # 处理新出现的股票
    codepre_list = get_codepre_list(connect, marketid, quotations)

    today = datetime.date.today()
    today = today.year * 10000 + today.month * 100 + today.day
    count = 0
    for code in newStockDict:
        if code not in oldStockDict:
            for codepre in codepre_list:
                length = len(codepre[0])
                if code[:length] == codepre[0]:
                    count += 1
                    #print(market, code, newStockDict[code], codepre)
                    sql = "insert into Stock(marketid, code, name, type, valid, startDate, endDate) \
                           values (%s, '%s', '%s', %s, %s, %s, %s)" \
                          % (marketid, code, newStockDict[code], codepre[1], 1, today, 99999999)
                    cur.execute(sql)
                    break

    #print('%s新增股票数：%i' % (market.upper(), count))
    connect.commit()
    cur.close()
    return count


def tdx_import_day_data_from_file(connect, filename, h5file, market, stock_record, end_date=None):
    """从通达信盘后数据导入日K线

    :param connect : sqlite3连接实例
    :param filename: 通达信日线数据文件名
    :param h5file  : HDF5 file
    :param stock_record: 股票的相关数据 (stockid, marketid, code, valid, type)
    :param end_date: 结束日期，格式为整数，如 20240401，如果指定，则跳过大于等于此日期的数据
    :return: 导入的记录数
    """
    add_record_count = 0
    if not os.path.exists(filename):
        return add_record_count

    stockid, marketid, code, valid, stktype = stock_record[0], stock_record[1], stock_record[
        2], stock_record[3], stock_record[4]

    table = get_h5table(h5file, market, code)
    if table.nrows > 0:
        lastdatetime = table[-1]['datetime'] / 10000
    else:
        lastdatetime = None

    row = table.row
    with open(filename, 'rb') as src_file:
        data = src_file.read(32)
        while data:
            record = struct.unpack('iiiiifii', data)
            if lastdatetime and record[0] <= lastdatetime:
                data = src_file.read(32)
                continue
                
            # 如果设置了结束日期，则跳过大于等于结束日期的记录
            if end_date and record[0] >= end_date:
                data = src_file.read(32)
                continue

            if 0 not in record[1:5]:
                if record[2] >= record[1] >= record[3] \
                        and record[2] >= record[4] >= record[3]:
                    row['datetime'] = record[0] * 10000
                    row['openPrice'] = record[1] * 10
                    row['highPrice'] = record[2] * 10
                    row['lowPrice'] = record[3] * 10
                    row['closePrice'] = record[4] * 10
                    row['transAmount'] = round(record[5] * 0.001)
                    if stktype == 2:
                        # 指数
                        row['transCount'] = record[6]
                    else:
                        row['transCount'] = round(record[6] * 0.01)

                    row.append()
                    add_record_count += 1

            data = src_file.read(32)

    if add_record_count > 0:
        table.flush()

        #更新基础信息数据库中股票对应的起止日期及其有效标志
        #if valid == 0:
        cur = connect.cursor()
        cur.execute(
            "update stock set valid=1, startdate=%i, enddate=%i where stockid=%i" %
            (table[0]['datetime']//10000, 99999999, stockid)
        )
        connect.commit()

    return add_record_count


def tdx_import_min_data_from_file(connect, filename, h5file, market, stock_record, end_date=None):
    """从通达信盘后数据导入1分钟或5分钟K线

    :param connect : sqlite3连接实例
    :param filename: 通达信K线数据文件名
    :param h5file  : HDF5 file
    :param stock_record: 股票的相关数据 (stockid, marketid, code, valid, type)
    :param end_date: 结束日期，格式为整数，如 20240401，如果指定，则跳过大于等于此日期的数据
    :return: 导入的记录数
    """
    add_record_count = 0
    if not os.path.exists(filename):
        return add_record_count

    stockid, marketid, code, valid, stktype = stock_record[0], stock_record[1], stock_record[
        2], stock_record[3], stock_record[4]

    table = get_h5table(h5file, market, code)
    if table.nrows > 0:
        lastdatetime = table[-1]['datetime']
    else:
        lastdatetime = None

    row = table.row
    with open(filename, 'rb') as src_file:
        def __get_date_time(pos):
            src_file.seek(pos * 32, SEEK_SET)
            data = src_file.read(32)
            if data:
                record = struct.unpack('hhiiifii', data)
                return record[2]
            return None

        file_size = os.path.getsize(filename)
        file_record_count = file_size // 32
        if file_record_count < 1:
            return add_record_count

        if file_record_count > 8:
            # 判断是否为1分钟线
            is_1min = False
            pos = file_record_count - 1
            date_time = __get_date_time(pos)
            if not date_time:
                return add_record_count

            date_time2 = __get_date_time(pos - 1)
            if not date_time2:
                return add_record_count

            if date_time // 1000000 == date_time2 // 1000000:
                # 同一天
                if date_time % 1000000 - date_time2 % 1000000 == 100:
                    is_1min = True
            pos = 0
            src_file.seek(0)
            data = src_file.read(32)
            while data:
                record = struct.unpack('hhiiifii', data)
                date = record[2] // 1000000
                time = record[2] % 1000000
                if date < 1990 or date > 2050:
                    data = src_file.read(32)
                    continue

                # 过滤小于lastdatetime的记录
                cur_datetime = record[2]
                if lastdatetime and cur_datetime <= lastdatetime:
                    data = src_file.read(32)
                    continue
                    
                # 如果设置了结束日期，则跳过大于等于结束日期的记录
                if end_date and date >= end_date:
                    data = src_file.read(32)
                    continue

                if 0 not in record[3:6]:
                    if record[4] >= record[3] >= record[5] \
                            and record[4] >= record[6] >= record[5]:
                        row['datetime'] = cur_datetime
                        row['openPrice'] = record[3] * 10
                        row['highPrice'] = record[4] * 10
                        row['lowPrice'] = record[5] * 10
                        row['closePrice'] = record[6] * 10
                        row['transAmount'] = round(record[7] * 0.001)
                        if stktype == 2:
                            # 指数
                            row['transCount'] = record[8]
                        else:
                            row['transCount'] = round(record[8] * 0.01)

                        row.append()
                        add_record_count += 1

                data = src_file.read(32)

    if add_record_count > 0:
        table.flush()

    return add_record_count


def tdx_import_data(connect, market, ktype, quotations, src_dir, dest_dir, progress=ProgressBar, end_date=None):
    """导入通达信指定盘后数据路径中的K线数据。注：只导入基础信息数据库中存在的股票。

    :param connect   : sqlit3链接
    :param market    : 'SH' | 'SZ'
    :param ktype     : 'DAY' | '1MIN' | '5MIN'
    :param quotations: 'stock' | 'fund' | 'bond'
    :param src_dir   : 盘后K线数据路径，如上证5分钟线：D:\\Tdx\\vipdoc\\sh\\fzline
    :param dest_dir  : HDF5数据文件所在目录
    :param progress  : 进度显示函数
    :param end_date  : 结束日期，格式为整数，如 20240401，如果指定，则跳过大于等于此日期的数据
    :return: 导入记录数
    """
    add_record_count = 0
    market = market.upper()
    h5file = open_h5file(dest_dir, market, ktype)

    if ktype.upper() == "DAY":
        suffix = ".day"
        func_import_from_file = tdx_import_day_data_from_file
    elif ktype.upper() == "1MIN":
        suffix = ".lc1"
        func_import_from_file = tdx_import_min_data_from_file
    elif ktype.upper() == "5MIN":
        suffix = ".lc5"
        func_import_from_file = tdx_import_min_data_from_file

    marketid = get_marketid(connect, market)
    stktype_list = get_stktype_list(quotations)
    sql = "select stockid, marketid, code, valid, type from stock where marketid={} and type in {}".format(
        marketid, stktype_list
    )

    cur = connect.cursor()
    a = cur.execute(sql)
    a = a.fetchall()

    total = len(a)
    for i, stock in enumerate(a):
        if stock[3] == 0:
            if progress:
                progress(i, total)
            continue

        filename = src_dir + "\\" + market.lower() + stock[2] + suffix
        this_count = func_import_from_file(connect, filename, h5file, market, stock, end_date)
        add_record_count += this_count
        if this_count > 0:
            if ktype == 'DAY':
                update_hdf5_extern_data(h5file, market.upper() + stock[2], 'DAY')

        if progress:
            progress(i, total)

    connect.commit()
    h5file.close()
    return add_record_count


if __name__ == '__main__':

    import time
    starttime = time.time()

    src_dir = "D:\\TdxW_HuaTai"
    dest_dir = "c:\\stock"
    quotations = ['stock', 'fund']  #通达信盘后数据没有债券

    connect = sqlite3.connect(dest_dir + "\\stock.db")
    create_database(connect)

    add_count = 0

    print("导入股票代码表")
    add_count = tdx_import_stock_name_from_file(
        connect, src_dir + "\\T0002\\hq_cache\\shm.tnf", 'SH', quotations
    )
    add_count += tdx_import_stock_name_from_file(
        connect, src_dir + "\\T0002\\hq_cache\\szm.tnf", 'SZ', quotations
    )
    print("新增股票数：", add_count)

    print("\n导入上证日线数据")
    add_count = tdx_import_data(
        connect, 'SH', 'DAY', quotations, src_dir + "\\vipdoc\\sh\\lday", dest_dir
    )
    print("\n导入数量：", add_count)

    print("\n导入深证日线数据")
    add_count = tdx_import_data(
        connect, 'SZ', 'DAY', quotations, src_dir + "\\vipdoc\\sz\\lday", dest_dir
    )
    print("\n导入数量：", add_count)

    print("\n导入上证5分钟数据")
    add_count = tdx_import_data(
        connect, 'SH', '5MIN', quotations, src_dir + "\\vipdoc\\sh\\fzline", dest_dir
    )
    print("\n导入数量：", add_count)

    print("\n导入深证5分钟数据")
    add_count = tdx_import_data(
        connect, 'SZ', '5MIN', quotations, src_dir + "\\vipdoc\\sz\\fzline", dest_dir
    )
    print("\n导入数量：", add_count)

    print("\n导入上证1分钟数据")
    add_count = tdx_import_data(
        connect, 'SH', '1MIN', quotations, src_dir + "\\vipdoc\\sh\\minline", dest_dir
    )
    print("\n导入数量：", add_count)

    print("\n导入深证1分钟数据")
    add_count = tdx_import_data(
        connect, 'SZ', '1MIN', quotations, src_dir + "\\vipdoc\\sz\\minline", dest_dir
    )
    print("\n导入数量：", add_count)

    print("\n导入权息数据")
    print("正在下载权息数据...")
    import urllib.request
    net_file = urllib.request.urlopen(
        'http://www.qianlong.com.cn/download/history/weight.rar', timeout=60
    )
    dest_filename = dest_dir + '/weight.rar'
    with open(dest_filename, 'wb') as file:
        file.write(net_file.read())

    print("下载完成，正在解压...")
    os.system('unrar x -o+ -inul {} {}'.format(dest_filename, dest_dir))

    print("解压完成，正在导入...")
    add_count = qianlong_import_weight(connect, dest_dir + '/weight', 'SH')
    add_count += qianlong_import_weight(connect, dest_dir + '/weight', 'SZ')
    print("导入数量：", add_count)

    connect.close()

    endtime = time.time()
    print("\nTotal time:")
    print("%.2fs" % (endtime - starttime))
    print("%.2fm" % ((endtime - starttime) / 60))
