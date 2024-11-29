import random

# 读取聊天记录文件
def read_chat_log(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        chat_log = file.read()
    return chat_log

def check_legal(msg:str, blacklist:list):
    if len(msg) <= 3:
        return False
    if any(blacklist_item in msg for blacklist_item in blacklist):
        return False
    if msg.startswith('[') or msg.endswith(']') or msg.startswith('@'):
        return False
    return True

# 解析聊天记录，排除黑名单内容
def parse_chat_log(chat_log, blacklist):
    messages = []
    message_lines = []
    lines = chat_log.split("\n")
    
    for line in lines:
        line = line.strip()
        if line:  # 忽略空行
            message_lines.append(line)
        else:
            # 如果是空行，表示一条消息的结束
            if message_lines:
                # 消息内容，忽略第一行（信息行）
                content = "\n".join(message_lines[1:]).strip()
                # 检查消息长度和是否包含黑名单词条
                if check_legal(content, blacklist):
                    messages.append({"message": content})
                message_lines = []  # 重置消息内容列表

    # 检查最后一条消息（没有空行结尾时）
    if message_lines:
        content = "\n".join(message_lines[1:]).strip()
        if check_legal(content, blacklist):
            messages.append({"message": content})

    return messages

# 随机抽取N条消息
def get_random_messages(messages, n=50):
    return random.sample(messages, n)

# 将抽取的消息内容写入到文件（只保留正文内容）
def write_messages_to_file(messages, output_file):
    with open(output_file, 'w', encoding='utf-8') as file:
        for message in messages:
            file.write(f"{message['message']}\n")

# 读取多个文件
def process_multiple_files(file_paths, blacklist, n=50):
    all_messages = []
    
    for file_path in file_paths:
        chat_log = read_chat_log(file_path)
        messages = parse_chat_log(chat_log, blacklist)
        all_messages.extend(messages)  # 合并所有文件中的消息

    # 随机抽取指定数量的消息
    random_messages = get_random_messages(all_messages, n)
    return random_messages

# 主程序
def main(input_files, output_file, blacklist, n=50):
    # 处理多个文件并获得随机抽取的消息
    random_messages = process_multiple_files(input_files, blacklist, n)
    # 将结果写入输出文件
    write_messages_to_file(random_messages, output_file)

# 文件路径
input_files = ["./dataset/[mc] 西武第三共和国.txt", "./dataset/工业时代服务器群.txt"]  # 输入文件路径，替换为您的聊天记录文件路径
output_file = "./dataset/random_records.txt"  # 输出文件路径，您可以修改为任何文件名

# 黑名单内容（可以根据需要添加更多词条）
blacklist = ["撤回了", "https", "连接服务器"]

# 执行主程序
main(input_files, output_file, blacklist, 100)