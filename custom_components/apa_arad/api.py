import aiohttp

LOGIN_URL="https://user.croscloud.com/croscloudpwd/openid"
class ApaAradApi:
    def __init__(self,u,p):
        self.u=u; self.p=p; self.session=aiohttp.ClientSession()
    async def async_login(self):
        data={"selected_community":"APARAD.MYACCOUNT","username":self.u,"password":self.p,"rememberme":"on","croscloud_pwd":""}
        async with self.session.post(LOGIN_URL,data=data,allow_redirects=True) as r:
            return r.status==200
