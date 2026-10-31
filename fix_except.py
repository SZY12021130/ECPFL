import re

with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 run_experiment 的异常处理
old = '''        for round_num in range(num_rounds):
            if use_encryption:
                result = self.run_round_encrypted(round_num)
            else:
                result = self.run_round_plain(round_num)
            results.append(result)
            
            # 每5轮保存一次模型
            if (round_num + 1) % self.config['output']['save_interval'] == 0:
                self._save_model(round_num + 1)
        
        # 保存最终结果
        self._save_results()
        
        # 保存最终轮次的模型（避免只有中间 checkpoint 而没有最终模型）
        self._save_model(num_rounds)
        
        # 终端打印客户端参与统计（表格形式）'''

new = '''        try:
            for round_num in range(num_rounds):
                if use_encryption:
                    result = self.run_round_encrypted(round_num)
                else:
                    result = self.run_round_plain(round_num)
                results.append(result)
                
                # 每5轮保存一次模型
                if (round_num + 1) % self.config['output']['save_interval'] == 0:
                    self._save_model(round_num + 1)
        except KeyboardInterrupt:
            tag_warn(LogTag.SUMMARY, "实验被用户中断")
        except Exception as e:
            tag_warn(LogTag.SUMMARY, f"实验异常中断: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 无论是否完成，都保存已产生的中间结果
            self._save_results()
            if results:
                self._save_model(len(results))
            tag_info(LogTag.SUMMARY, f"实验结果已保存至: {self.output_dir}")
        
        # 终端打印客户端参与统计（表格形式）'''

if old in content:
    content = content.replace(old, new)
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Fixed run_experiment successfully')
else:
    print('Old string not found')
