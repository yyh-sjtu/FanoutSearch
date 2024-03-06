#导入依赖库
import numpy as np

######################################预处理########################################

# 读取文件
def read_file_multiblock(file_name):
    module_dic = {}
    top_module_name = file_name.split("/")[-1].split(".")[0]    # 识别顶层模块
    
    with open(file_name,'r') as f:  # 按模块拆分网表
        txt_module_block = f.read().split("endmodule")
    
    for module in txt_module_block[:-1]:
        module_txt = [i.replace('\n','').strip() for i in module.split(';')]
        module_name = extract_modulename(module_txt)
        module_dic[module_name] = module_txt[:-1]
        
    return top_module_name, module_dic

# 按模块名拆分模块
def extract_modulename(module_txt):
    if "/*" in module_txt[0]:
        module_txt[0] = module_txt[0].split("*/")[-1]
    module_name = module_txt[0][7:-1].split('(')[0] 
    return module_name

#########################################读图########################################

def sparse_module_ex(module_ex): # 生成例化模块的输出端口列表、每个输出端口所对应的输入端口列表
    outportlist = []
    inportlist = []
    for item_ex in module_ex.split(".")[1:]:
        outport = item_ex.split("(")[0].strip()
        if "{" in item_ex:
            inport = [i.strip().strip() for i in item_ex.split("{")[1].split("}")[0].split(",")]
        else:
            inport = [item_ex.split("(")[1].split(")")[0].strip()]
        outportlist.append(outport)
        inportlist.append(inport)
    return outportlist, inportlist


def extract_netlist(module_dic, module_name, recursion = 0,  
                    node_name_list = [], reg_index_list = [], index_wire = 0, 
                    index_node_count = 0, wire_dic = {}, wire_last_dic = {}, 
                    adj_list_node = [], adj_list_wire = [], IO_com_node_dic = {}, 
                    outportlist = [], inportlist = []):
    
    if recursion == 0:                  # 记录递归情况的flag，除了第一层是0，后面都是1
        index_wire = 0                  # 用于记录连线的全局索引
        index_node_count = 0            # 用于记录节点的全局索引
        node_name_list = []             # 用于存储全局的节点名称
        reg_index_list = []             # 用于存储全局的reg索引
        wire_dic = {}                   # 用于存储当前模块的连线信息
        wire_last_dic = {}              # 用于存储上一级模块的连线信息
        adj_list_node = []              # 用于存储全局的节点连接关系（邻接表）            
        adj_list_wire = []              # 用于存储全局的连线连接关系（邻接表）
        IO_com_node_dic = {}            # 用于存储当前模块的输入输出信息
        outportlist = []                # 用于存储模块间连接的输出信息（当前模块连线）
        inportlist = []                 # 用于存储模块间连接的输入信息（上一级模块连线）
        
    module_txt = module_dic[module_name]
    
    #处理input output 和 内部连线
    for index, i in enumerate(module_txt):
        if i[:7] == 'module ':    # 识别模块名
            module_split = i[7:-1].replace('(',',').split(',')
            module_IoList = [item.strip() for item in module_split[1:] ]

        elif i.split(' ')[0] == 'input':    # 产生输入端口列表
            if '[' in i:    # 检测是不是多位总线
                for item in range(int(i.split('[')[1].split(':')[0]) + 1):

                    currentnode = i.split(' ')[-1] + '[' + str(item) + ']'
                    
                    wire_dic.update({currentnode : index_wire})
                    adj_list_wire.append([])
                    
                    # 把IO既当作线又当作组合逻辑
                    IO_com_node_dic[currentnode] = [index_node_count, "input"]
                    adj_list_node.append([index_wire])
                    node_name_list.append(currentnode)
                    
                    index_wire += 1
                    index_node_count += 1
                    
            else:
                currentnode = i.split(' ')[-1]

                wire_dic.update({currentnode : index_wire})
                adj_list_wire.append([])
                
                # 把IO既当作线又当作组合逻辑
                IO_com_node_dic[currentnode] = [index_node_count, "input"]
                adj_list_node.append([index_wire])
                node_name_list.append(currentnode)
                
                index_wire += 1
                index_node_count += 1

        elif i.split(' ')[0] == 'output':   # 产生输出端口列表
            if '[' in i:    # 检测是不是多位总线
                for item in range(int(i.split('[')[1].split(':')[0]) + 1):
                    currentnode = i.split(' ')[-1] + '[' + str(item) + ']'

                    wire_dic.update({currentnode : index_wire})
                    adj_list_wire.append([])
                    
                    # 把IO既当作线又当作组合逻辑
                    IO_com_node_dic[currentnode] = [index_node_count, "output"]
                    adj_list_node.append([])
                    adj_list_wire[-1].append(index_node_count)
                    node_name_list.append(currentnode)
                    
                    index_wire += 1
                    index_node_count += 1
                    
            else:
                currentnode = i.split(' ')[-1]
                wire_dic.update({currentnode : index_wire})
                adj_list_wire.append([])
                
                # 把IO既当作线又当作组合逻辑
                IO_com_node_dic[currentnode] = [index_node_count, "output"]
                adj_list_node.append([])
                adj_list_wire[-1].append(index_node_count)
                node_name_list.append(currentnode)
                
                index_wire += 1
                index_node_count += 1
                
        elif (i.split(' ')[0] == 'wire') & ~(i.split(' ')[-1] in module_IoList):    # 产生内部连线列表
            currentnode=i.split(' ')[-1]

            wire_dic.update({currentnode : index_wire})
            index_wire += 1
            adj_list_wire.append([])

        elif 'sky130' in i:
            break

    # 与调用此模块的外部模块合并
    for outport, inports in zip(outportlist, inportlist):    # 对输人/输出端口列表迭代
        lenitem = len(inports)
        if lenitem > 1:     # 检查输出端口对应的输入端口的数量
            for index_inport, inport in enumerate(inports):
                outsingle_wire = outport + "[" + str(lenitem-1-index_inport) + "]"  # 上层模块的线 —— 子模块的线      
                if IO_com_node_dic[outsingle_wire][1] == "input": # 在当前模块为输入线，则把当前连接线作为上层模块对应线的子节点
                    adj_list_wire[wire_last_dic[inport] ].append(IO_com_node_dic[outsingle_wire][0]) # 
                else:   # 在当前模块为输出线，则把上层模块的连接线作为当前输出线节点的输出
                    adj_list_node[IO_com_node_dic[outsingle_wire][0] ].append(wire_last_dic[inport]) # 
                    
        else:
            if outport + "[" + str(0) + "]" in IO_com_node_dic.keys():    # 连接线组相互赋值
                count_wire = 0
                outsingle_wire = outport + "[" + str(count_wire) + "]"
                while outsingle_wire in IO_com_node_dic.keys():
                    insingle_wire = inports[0] + "[" + str(count_wire) + "]"
                        
                    if IO_com_node_dic[outsingle_wire][1] == "input":
                        adj_list_wire[wire_last_dic[insingle_wire] ].append(IO_com_node_dic[outsingle_wire][0])
                    else:
                        adj_list_node[IO_com_node_dic[outsingle_wire][0] ].append(wire_last_dic[insingle_wire])
                            
                    count_wire += 1
                    outsingle_wire = outport + "["+str(count_wire)+"]"

            else:
                if IO_com_node_dic[outport][1] == "input":
                    adj_list_wire[wire_last_dic[inports[0] ] ].append(IO_com_node_dic[outport][0])
                else:
                    adj_list_node[IO_com_node_dic[outport][0] ].append(wire_last_dic[inports[0] ])
    
        
    for item in module_txt[index:]:
        module_type_name = item.split(' ')[0]
            
        # 处理门电路
        if 'sky130' in module_type_name: 
            c_node_list = item.split(' (')[0]
            node_wire_outsub = [subitem.split(')')[0].strip() for subitem in item.split('(')[2:]]
                    
            adj_list_node.append([])
            node_name_list.append(c_node_list)
                    
            if "dfrtp" in c_node_list or "dfstp" in c_node_list or "dfxtp" in c_node_list:
                reg_index_list.append(index_node_count)
                        
                if "dfrtp" in c_node_list or "dfstp" in c_node_list:
                    node_wire_outsub[-1], node_wire_outsub[-2] = node_wire_outsub[-2], node_wire_outsub[-1]
                    
            for item in node_wire_outsub[:-1]:
                adj_list_wire[wire_dic[item] ].append(index_node_count)            
                    
            adj_list_node[-1].append(wire_dic[node_wire_outsub[-1] ])
            index_node_count += 1
            
        # 递归处理例化模块
        elif  module_type_name in module_dic.keys():
            outportlist, inportlist = sparse_module_ex(item)
            print(module_name, "call", module_type_name)
            index_wire, index_node_count, adj_list_node, \
                adj_list_wire, node_name_list, reg_index_list, \
                outportlist, inportlist = extract_netlist(module_dic, module_type_name, 1, 
                                                            node_name_list, reg_index_list, index_wire, 
                                                            index_node_count, {}, wire_dic, 
                                                            adj_list_node, adj_list_wire, {}, 
                                                            outportlist, inportlist) 
        
        else:
            print('error module')

    # 递归结束，去除wire node直接将单元门node进行连接的操作
    if recursion == 0:
        for i in range(len(adj_list_node)):
            if adj_list_node[i]:
                adj_list_node[i] = adj_list_wire[adj_list_node[i][0]]
    
    return index_wire, index_node_count, adj_list_node, \
            adj_list_wire, node_name_list, reg_index_list, \
            outportlist, inportlist

#分裂邻接表
def split_adj_list(adj_list_lite, class_reg_list):
    adj_reg_list = []
    adj_com_list = []

    for i in range(len(adj_list_lite)):
        fanout_reg = []
        fanout_com = []
        for idx in adj_list_lite[i]:
            if (idx in class_reg_list):  # 寄存器类型
                fanout_reg.append(idx)
            else:  # 组合逻辑类型
                fanout_com.append(idx)
        adj_reg_list.append(fanout_reg)
        adj_com_list.append(fanout_com)
    return adj_reg_list, adj_com_list


########################################精确搜索算法##########################################

def fanout_adj_list(adj_reg_list, adj_com_list, class_reg_list):
    record=[] #记录结果

    for item_index_reg in class_reg_list: #遍历寄存器节点
        currentnode = np.array([item_index_reg], dtype=int) #当前准备作为出发点的节点，初始化为正要遍历的寄存器节点
        fanout_reg = np.empty([0], dtype = int) #还没有被算为扇出寄存器的寄存器，初始化为全部寄存器节点的索引

        while(np.shape(currentnode)[0] > 0):
            nextnode = np.array([i2 for i1 in currentnode for i2 in adj_com_list[i1] ])
            regnode = np.array([i2 for i1 in currentnode for i2 in adj_reg_list[i1] ])
            
            currentnode = np.unique(nextnode)
            fanout_reg = np.union1d(fanout_reg, regnode)

        record.append([item_index_reg, np.shape(fanout_reg)[0]]) #记录结果

    return record

