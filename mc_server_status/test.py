import pandas as pd
from os import path

admin_list = pd.read_csv(path.dirname(path.abspath(__file__)) + "\\admin.csv")      # 管理员表
super_admins = admin_list[admin_list['groupId'] == 0]['qid'].values                 # 全局管理员清单
print(admin_list)

new_row = pd.DataFrame([{
        "qid": 2,
        "groupid": 1
    }])

tar_index = 1
up_list = admin_list.iloc[:tar_index+1]
bot_list = admin_list.iloc[tar_index+1:]
admin_list = pd.concat([up_list, new_row, bot_list]).reset_index(drop=True)
print(admin_list)