import time
from functools import cached_property
from threading import Thread

import Ice


class IceTestMixin:
    def ice_initialize_with_props(self, props_dict):
        init_data = Ice.InitializationData()
        init_data.properties = Ice.createProperties()
        for k, v in props_dict.items():
            init_data.properties.setProperty(k, v)

        return Ice.initialize(init_data)

    def wait_object_ready(self, proxy):
        proxy = proxy.ice_timeout(500)
        for _ in range(3):
            try:
                proxy.ice_ping()
                return
            except Ice.Exception:
                time.sleep(0.5)

        self.fail('Object not ready after 3 attempts')

    @cached_property
    def client_ic(self):
        client_ic = Ice.initialize()
        self.addCleanup(client_ic.destroy)
        return client_ic

    def create_proxy(self, proxy_str, cast):
        proxy = self.client_ic.stringToProxy(proxy_str)
        self.wait_object_ready(proxy)
        proxy = cast.checkedCast(proxy)
        self.assertIsNotNone(proxy)
        return proxy

    def create_server(self, main, props, *args):
        ic = self.ice_initialize_with_props(props)
        args = (ic,) + args
        thread = Thread(target=main, args=args)
        thread.start()
        self.addCleanup(ic.shutdown)
