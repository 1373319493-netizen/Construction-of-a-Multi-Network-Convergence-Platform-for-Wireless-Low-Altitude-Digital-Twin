import helics as h

# 创建 federate
fed = h.helicsCreateValueFederateFromConfig(
    "/mnt/c/Users/13733/Desktop/毕设相关/rayget/fed.json"
)
print("Federate created!")

# 获取 publication
pub = h.helicsFederateGetPublication(fed, "example_pub")
print("Publication acquired:", pub)

# 发送数据
h.helicsPublicationPublishDouble(pub, 123.45)
print("Published 123.45")

# 进入模拟时间
h.helicsFederateEnterExecutingMode(fed)
print("Federate executing")

# 关闭 federate
h.helicsFederateFinalize(fed)
print("Federate finalized")