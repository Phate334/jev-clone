from jev import Noul, TypeSafeClient


with TypeSafeClient() as client:
    result = client.system_one(
        state="所有使用者都無法登入",
        questions={"escalate": Noul(instructions="是否需要立即通知值班工程師？")},
    )
    print(result.nouls["escalate"].noul)
