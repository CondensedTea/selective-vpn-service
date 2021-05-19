import asyncio


class WireGuard:
    async def run(self, cmd: str) -> None:
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()

    async def set_peer(self, pubkey: str, server_inbound_ip: int) -> None:
        cmd = f'wg set wg0 peer {pubkey} allowed-ips 192.168.20.{server_inbound_ip}'
        print(cmd)
        await self.run(cmd)
