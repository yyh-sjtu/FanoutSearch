import verilog_reader_package as vrn
import pandas as pd
import time
import os

print('----开始运行脚本----')

print('----读文件----')

#输入文件地址
file_name_list=["zipdiv.v","usb_cdc_core.v","usb.hierarchy.v","picorv32.v"]
fold_name="./verilog_netlist_for_test/"
file_name=fold_name+file_name_list[3]

#创建目录
directory='./Result_fanout'
if not os.path.exists(directory):
    os.makedirs(directory)

#读文件
with open(file_name,'r') as f:
        txt_module_block=f.read().split("endmodule")

module_name_whole=[] #模块名
module_dic={} #文件中定义的各个module

#读文件
top_module_name, module_dic1 = vrn.read_file_multiblock(file_name)

#提取网表并转换成基于邻接表的图
start = time.time()
index_wire1, index_node_count1, adj_list_node1, \
    adj_list_wire1, wire_node_name_list_node1, class_reg_list_node1, \
    outportlist1, inportlist1 = vrn.extract_netlist(module_dic1, top_module_name, recursion = 0)
end = time.time()
print('time of reading graph:', end - start)

#分裂邻接表
adj_reg_list_node1, adj_com_list_node1 = vrn.split_adj_list(adj_list_node1, class_reg_list_node1)

#运行扇出搜索算法
start = time.time()
record_nodewire2 = vrn.fanout_adj_list(adj_reg_list_node1, adj_com_list_node1, class_reg_list_node1)
end = time.time()
print('time of searching fanout:', end - start)

#生成寄存器扇出搜索报告
outlist=[ [ i[0] , wire_node_name_list_node1[i[0]] , i[1] ] for i in record_nodewire2]
outlistdf = pd.DataFrame(outlist)
outlistdf = outlistdf.rename(columns={0: 'index', 1: 'name of standard cell', 2: 'number of fanout'})
outpath=os.path.join(directory,str(file_name.split("/")[-1].replace(".v",""))+".csv")
# 扇出信息的DataFrame存为.csv
outlistdf.to_csv(outpath)