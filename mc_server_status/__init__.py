"""
一个尚且不完善的minecraft服务器插件, 
用于查询不同群的服务器信息并以图片形式返回ip, ping, 玩家列表信息。
"""
from nonebot import on_keyword, on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Event
from nonebot.adapters.onebot.v11.message import Message
from nonebot.params import CommandArg, ArgPlainText
from mcstatus import JavaServer, BedrockServer
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
from os import path
from time import localtime, strftime, time
import base64, io

# 资源加载
sourceFile = path.dirname(path.abspath(__file__)) + "\\source"
fontPath = sourceFile + "\\minecraft.ttf"
server_list = pd.read_csv(path.dirname(path.abspath(__file__)) + "\\server.csv")    # 服务器表
admin_list = pd.read_csv(path.dirname(path.abspath(__file__)) + "\\admin.csv")      # 管理员表
super_admins = admin_list[admin_list['groupId'] == 0]['qid'].values                 # 全局管理员清单
groups = set(server_list['qid'])                                                    # 需要用到此插件的群组

# 变量初始化
CHECKED = False     # 是否在启动后检测过至少一次
old_t = time()      # 用于记录上次检测时间，防止生成图片过快风控
tmp_info = ""
tmp_index = -1

def get_size(text, font):
    """获得text实际渲染宽度"""
    canvas = Image.new('RGB', (800,100))
    draw = ImageDraw.Draw(canvas)
    draw.text((0, 0), text, font=font, fill=(255, 255, 255))
    frame = canvas.getbbox()
    assert frame is not None
    size = frame[2] - frame[0]
    del canvas
    return size

async def server_check(event: GroupMessageEvent):
    """查询是否在特定qq号群聊内询问"""
    return event.group_id in groups

async def admin_check(event: GroupMessageEvent):
    """查询是否为超管/对应群管理"""
    return event.group_id in groups and (
        event.user_id in super_admins or 
        event.user_id in admin_list[admin_list['groupId'] == event.group_id].values
    )

# 唤起指令
lookUp = on_keyword(set(["服务器信息"]), rule=server_check, priority=1)
addOp = on_command("添加管理员", rule=admin_check, priority=1)
removeOp = on_command("移除管理员", rule=admin_check, priority=1)
modIp = on_command("改ip", rule=admin_check, priority=1)
addIp = on_command("加ip", rule=admin_check, priority=1)

@lookUp.handle()
async def get_information(event: Event):
    """
    ## 查询服务器信息指令。
    - 查询方式: 匹配 "服务器信息" 字符串;
    - 响应方式: 回应包含所需全部ip的对应图片.
    - 返回的图片如果成功生成, 会被保存为./source/res.png
    """
    global CHECKED, old_t, server_list
    t = time()
    if (CHECKED is True and t - old_t <= 30):
        await lookUp.finish(Message(f"查询太频繁了喵~ ({int(30 - t + old_t)}秒后)"))
    else:
        old_t = t
        CHECKED = True
        await lookUp.send(Message(f"收到, 连接服务器中~ (可能要等一小会喵)"))

    groupid = int(event.get_session_id().split("_")[1])
    tmpDF = server_list[server_list['qid'] == groupid].values     # 找出特定群组的服务器信息

    servers = []
    print("======服务器信息查询中======")
    for i in range(len(tmpDF)):
        try:
            if (tmpDF[i][2] == 'j'):
                server = await JavaServer.async_lookup(tmpDF[i][1])
                data = server.status()      # 各项状态
                ping = int(data.latency)
                ver = data.version.name     # 版本名
                playerList = []             # 玩家列表
                if data.players.online:
                    if data.players.sample:
                        playerList = [
                            p.name for p in data.players.sample
                            if p.id != "00000000-0000-0000-0000-000000000000"
                        ]
                if (data.icon is not None):
                    ico = Image.open(io.BytesIO(base64.b64decode(data.icon.removeprefix("data:image/png;base64,")))).resize((128, 128))
                else:
                    ico = Image.open(sourceFile + "\\unknown_server.png")
                # versionMark(1 for Java, 2 for Bedrock), Name, Version, IP, ping, capacity, icon, playerlist
                servers.append([1, tmpDF[i][3], ver, tmpDF[i][1], ping, data.players.max, ico, playerList])
            else:
                server = BedrockServer.lookup(tmpDF[i][1])
                data = server.status()      # 各项状态
                ping = int(data.latency)    # 延迟(ms)
                ver = data.version.name     # 版本名
                ico = Image.open(sourceFile + "\\BE_default.png")
                # versionMark(1 for Java, 2 for Bedrock), Name, Version, IP, ping, capacity, icon, playercount
                servers.append([2, tmpDF[i][3], ver, tmpDF[i][1], ping, data.players.max, ico, data.players_online])

        except Exception as e:
            # SuccessMark, Name, ver, IP, offline mark, fail_info
            response = repr(e)
            if (len(response) > 32): 
                response = response[:32] + "..."
            servers.append([False, tmpDF[i][3], "Unknown", tmpDF[i][1], "offline", response])
            print(f"服务器{tmpDF[i][3]}[IP:{tmpDF[i][1]}]查询失败，原因: {repr(e)}")

    # 根据服务器信息生成回答图片
    colors = [(238, 44, 44), (102, 205, 0), (225, 225, 225), (150, 150, 150), (255, 215, 0)]
    resImg = Image.new("RGB", (1024, 192 * (len(servers) + 1)))
    # 回答图片顶部标题栏
    top = Image.open(sourceFile + "\\top.png")
    resImg.paste(top, (0, 0))
    del top
    
    # 生成每行信息
    for i in range(len(servers)):
        if servers[i][0] == 1:   # Query Success
            # Name, Version, IP, ping, capacity
            info = servers[i][1:6]
            ico = servers[i][6]
            players = servers[i][-1]

            fast = info[4] < 150
            info[3] = str(info[3]) + " ms"
            info[4] = f"玩家数量: {len(players)}/{info[4]}"
            if len(players) == 0:
                info.append("#服务器内无玩家#")
                NOONE = True
            else:
                listPlayer = f"在线玩家: {players[0]}"
                for j in range(1, min(2, len(players))):
                    listPlayer += ", " + players[j]
                if (len(players) > 2):
                    listPlayer += ", ..."
                info.append(listPlayer)
                NOONE = False
            
            img = Image.open(sourceFile + "\\middle.png")
            tmpmid = ImageDraw.Draw(img)

            size = [30, 20, 20, 35, 20, 20]
            size_5 = get_size(info[5], font=ImageFont.truetype(fontPath, size[5]))
            size_4 = get_size(info[4], font=ImageFont.truetype(fontPath, size[4]))
            pos = [(200, 30), (200, 115), (200, 80), (825, 35), (960 - size_4 - 1.5, 85), (960 - size_5, 120)]
            cmap = [2, 2, 2, fast, 2, 2 + NOONE]
            for ti in range(6):
                tmpmid.text(pos[ti], info[ti], fill=colors[cmap[ti]], font=ImageFont.truetype(fontPath, size[ti]))
            img.paste(ico,(30, 30))
            print(f"服务器{info[0]}完整玩家列表: ", players)

        elif servers[i][0] == 2:
            # Name, Version, IP, ping, capacity
            info = servers[i][1:6]
            ico = servers[i][6]
            players = servers[i][-1]

            fast = info[4] < 150
            info[1] += " (Bedrock)"
            info[3] = str(info[3]) + " ms"
            info[4] = f"玩家数量: {players}/{info[4]}"
            
            img = Image.open(sourceFile + "\\middle.png")
            tmpmid = ImageDraw.Draw(img)

            size = [30, 20, 20, 35, 20]
            size_4 = get_size(info[4], font=ImageFont.truetype(fontPath, size[4]))
            pos = [(200, 30), (200, 115), (200, 80), (825, 35), (960 - size_4 - 1.5, 85)]
            cmap = [2, 2, 2, fast, 2]
            for ti in range(5):
                tmpmid.text(pos[ti], info[ti], fill=colors[cmap[ti]], font=ImageFont.truetype(fontPath, size[ti]))
            img.paste(ico,(30, 30))

        else:   # Query Fail
            # Name, ver, IP, offline mark, fail_info
            info = servers[i][1:]

            img = Image.open(sourceFile + "\\middle.png")
            tmpmid = ImageDraw.Draw(img)

            size = [30, 20, 20, 35, 20]
            size_4 = get_size(info[4], font=ImageFont.truetype(fontPath, size[4]))
            pos = [(200, 30), (200, 115), (200, 80), (825, 35), (960 - size_4 - 1.5, 85)]
            cmap = [2, 2, 2, 0, 2]
            for ti in range(5):
                tmpmid.text(pos[ti], info[ti], fill=colors[cmap[ti]], font=ImageFont.truetype(fontPath, size[ti]))
            ico = Image.open(sourceFile + "\\unknown_server.png")
            img.paste(ico,(30, 30))

        # adding rows of server infos
        resImg.paste(img, (0, 128 + i * 192))
        del img, tmpmid
    # 末尾时间/群聊标记
    end = Image.open(sourceFile + "\\end.png")

    tmpend = ImageDraw.Draw(end)
    curtime = strftime("%Y-%m-%d %H:%M", localtime())
    callSign = f"查询群号: {groupid}  时间: {curtime}"
    endSize = get_size(callSign, ImageFont.truetype(fontPath, 20))
    tmpend.text((512 - endSize / 2, 20), callSign, fill=(255, 255, 255), font=ImageFont.truetype(fontPath, 20))

    resImg.paste(end, (0, 128 + 192 * len(servers)))
    
    resImg.save(sourceFile + "\\res.png")

    print("存储入res.png成功")
    print("======查询结束======")

    await lookUp.finish(Message(f"[CQ:image,file=file:///{sourceFile}\\res.png]"))

@addOp.handle()
async def add_admin(event: Event, args=CommandArg()):
    """
    ## 添加管理员指令
    - 唤起方法: 指令 "/添加管理员 {qq号}"
    - 响应: 提示添加成功/失败
    """
    try:
        new_adminId = int(str(args))
    except:
        await addOp.finish("看不懂喵...需要在\"添加管理员\"后附加qq号码捏...")
    groupId = int(event.get_session_id().split("_")[1])
    # 添加行并保存
    global admin_list, super_admins
    admin_list.loc[len(admin_list)] = [new_adminId, groupId]
    admin_list.to_csv(path.dirname(path.abspath(__file__)) + "\\admin.csv", index=False)
    admin_list = pd.read_csv(path.dirname(path.abspath(__file__)) + "\\admin.csv")
    # 返回信息
    admin_num = len(admin_list[admin_list['groupId'] == groupId]) + len(super_admins)
    await addOp.finish(Message(f"添加群管理员成功喵, 当前本群管理共有{admin_num}人~"))

@removeOp.handle()
async def remove_admin(event: Event, args=CommandArg()):
    """
    ## 移除管理员指令
    - 唤起方法: 指令 "/移除管理员 {qq号}"
    - 响应: 提示移除成功/失败
    """
    try:
        rem_adminId = int(str(args))
    except:
        await addOp.finish("看不懂喵...需要在\"添加管理员\"后附加qq号码捏...")
    groupId = int(event.get_session_id().split("_")[1])
    global admin_list, super_admins
    admin_list = admin_list[(admin_list['qid'] != rem_adminId) | (admin_list['groupId'] != groupId)]
    admin_list.to_csv(path.dirname(path.abspath(__file__)) + "\\admin.csv", index=False)
    admin_list = pd.read_csv(path.dirname(path.abspath(__file__)) + "\\admin.csv")

    admin_num = len(admin_list[admin_list['groupId'] == groupId]) + len(super_admins)
    await addOp.finish(Message(f"群管理员减员成功喵, 当前本群管理共有{admin_num}人~"))

@modIp.got("num", prompt="想要更改第几个服务器的ip? (只回复序号数字即可, 回复“列表”查看对应序号)")
async def change_Ip(event: Event, num=ArgPlainText()):
    global server_list, tmp_index, tmp_info
    
    groupId = int(event.get_session_id().split("_")[1])
    names = server_list[server_list['qid'] == groupId]['name'].values
    tmp_index = len(names)  # 暂存最大序号

    if num == "列表":
        tmp_info += "检测到本群共有如下服务器:\n"
        for i in range(len(names)):
            tmp_info += f"{i+1}. {names[i]}\n"
        tmp_info += "想要更改第几个服务器的Ip?"
        await modIp.reject(tmp_info)

    try:
        req_index = int(num) - 1
    except:
        await modIp.finish("看不懂这是第几个喵")
    
    if req_index >= tmp_index:
        await modIp.finish("没这么多服务器喵")
    
    groupId = int(event.get_session_id().split("_")[1])
    tmp_index = server_list[server_list['qid'] == groupId].index[req_index]

@modIp.got("addr", prompt="想要改成什么ip? (只回复ip即可, 回复\"0\"删除该条ip)")
async def new_Ip(addr=ArgPlainText()):
    global server_list, tmp_index, tmp_info
    if addr == "0":
        server_list = server_list.drop(index=tmp_index).reset_index(drop=True)
    else:
        server_list.loc[tmp_index, 'ip'] = addr
    # 重新读取文件
    server_list.to_csv(path.dirname(path.abspath(__file__)) + "\\server.csv", index=False)
    tmp_info = ""
    await modIp.finish("更改ip完成捏")

@addIp.got("info", prompt="请按\"名字 ip地址 版本号\"描述你想添加的服务器, 以单个空格分隔。\n(版本号只需要输入单个字母 j 或 b , 分别表示服务端是java/基岩版)")
async def add_Ip(event: Event, info=ArgPlainText()):
    global server_list
    # info: [名字, ip, 版本号]
    info = info.rsplit(' ', 2)
    if (len(info) != 3 or info[2] not in ["J", "j", "B", "b"]):
        await addIp.finish("看不懂喵, 请重新输入/加ip。")
    
    groupid = int(event.get_session_id().split("_")[1])
    tar_index = server_list[server_list['qid'] == groupid].index[-1]

    new_row = pd.DataFrame([{
        "qid": groupid,
        "ip": info[1],
        "ver": info[2].lower(),
        "name": info[0]
    }])

    up_list = server_list.iloc[:tar_index+1]
    bot_list = server_list.iloc[tar_index+1:]
    server_list = pd.concat([up_list, new_row, bot_list]).reset_index(drop=True)
    
    server_list.to_csv(path.dirname(path.abspath(__file__)) + "\\server.csv", index=False)
    query_size = len(server_list[server_list['qid'] == groupid].index)
    await addIp.finish(f"录入成功喵, 当前本群共记录了{query_size}条ip。")
