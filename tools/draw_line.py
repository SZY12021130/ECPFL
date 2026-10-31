from tools.plotter import Plotter

p = Plotter(style=["science"])

# 只画一张图
p.line(
    data={
        "FedAvg": {"x": [10,20,30,40,50], "y": [0.50,0.60,0.65,0.70,0.72]},
        "Ours":   {"x": [10,20,30,40,50], "y": [0.52,0.62,0.68,0.73,0.76]},
    },
    xlabel="Round",
    ylabel="Accuracy",
    filename="my_result"   # 自动保存为 my_result.png + my_result.pdf
)