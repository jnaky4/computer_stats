from flask import Flask, jsonify
import subprocess
import platform
import psutil
from datetime import datetime, timedelta
import time
import os
import GPUtil
import cpuinfo
import pyamdgpuinfo
# import pyadl
# from pyadl import ADLManager

#TODO Get tuples from _common.py
def psutil_stats():
    return {
        # "fans": psutil.sensors_fans(),

        'cpu': {
            "cores": psutil.cpu_count(),
            'load_average (min)': {
                "1": psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else None,
                "5": psutil.getloadavg()[1] if hasattr(psutil, 'getloadavg') else None,
                "15": psutil.getloadavg()[2] if hasattr(psutil, 'getloadavg') else None,
            },
            "stats": {
                "ctx_switches": psutil.cpu_stats().ctx_switches if hasattr(psutil.cpu_stats(), 'ctx_switches') else None,
                "interrupts": psutil.cpu_stats().interrupts if hasattr(psutil.cpu_stats(), 'interrupts') else None,
                "soft_interrupts": psutil.cpu_stats().soft_interrupts if hasattr(psutil.cpu_stats(), 'soft_interrupts') else None,
                "syscalls": psutil.cpu_stats().syscalls if hasattr(psutil.cpu_stats(), 'syscalls') else None
            },
            "info": cpuinfo.get_cpu_info(),
            "times": {
                "per_cpu (sec)": [
                    {
                        "user": cpu_times.user,
                        "system": cpu_times.system,
                        "idle": cpu_times.idle,
                        "nice": cpu_times.nice if hasattr(cpu_times, 'nice') else None,
                        "iowait": cpu_times.iowait if hasattr(cpu_times, 'iowait') else None,
                        "irq": cpu_times.irq if hasattr(cpu_times, 'irq') else None,
                        "softirq": cpu_times.softirq if hasattr(cpu_times, 'softirq') else None,
                        "steal": cpu_times.steal if hasattr(cpu_times, 'steal') else None,
                        "guest": cpu_times.guest if hasattr(cpu_times, 'guest') else None,
                        "guest_nice": cpu_times.guest_nice if hasattr(cpu_times, 'guest_nice') else None
                    } for cpu_times in psutil.cpu_times(percpu=True)
                ]
            },
            "freq (Mhz)": {
                "curr": int(psutil.cpu_freq()[0]),
                "min": int(psutil.cpu_freq()[1]),
                "max": int(psutil.cpu_freq()[2]),

            },
        },
        # sane as file systems
        # 'disks': {
        #     disk.device: {
        #         "total": psutil.disk_usage(disk.mountpoint).total,
        #         "used": psutil.disk_usage(disk.mountpoint).used,
        #         "free": psutil.disk_usage(disk.mountpoint).free,
        #         "used %": psutil.disk_usage(disk.mountpoint).percent
        #     } for disk in psutil.disk_partitions()
        # },
        'disk_io': {
            disk: {
                "read_count": counters.read_count,
                "write_count": counters.write_count,
                "read_bytes": counters.read_bytes,
                "write_bytes": counters.write_bytes,
                "read_time": counters.read_time,
                "write_time": counters.write_time
            } for disk, counters in psutil.disk_io_counters(perdisk=True).items()
        },
        'file_systems': {
            partition.mountpoint: {
                'device': partition.device,
                'fstype': partition.fstype,
                'opts': partition.opts,
                'total': psutil.disk_usage(partition.mountpoint).total,
                'used': psutil.disk_usage(partition.mountpoint).used,
                'free': psutil.disk_usage(partition.mountpoint).free,
                'percent': psutil.disk_usage(partition.mountpoint).percent
            } for partition in psutil.disk_partitions()
        },

        'memory (bytes)': { #todo in b Mb Gb?
            "total": psutil.virtual_memory().total,
            "available": psutil.virtual_memory().available,
            "percent": psutil.virtual_memory().percent,
            "used": psutil.virtual_memory().used,
            "free": psutil.virtual_memory().free,
            "active": psutil.virtual_memory().active if hasattr(psutil.virtual_memory(), 'active') else None,
            "inactive": psutil.virtual_memory().inactive if hasattr(psutil.virtual_memory(), 'inactive') else None,
            "buffers": psutil.virtual_memory().buffers if hasattr(psutil.virtual_memory(), 'buffers') else None,
            "cached": psutil.virtual_memory().cached if hasattr(psutil.virtual_memory(), 'cached') else None,
            "wired": psutil.virtual_memory().wired if hasattr(psutil.virtual_memory(), 'wired') else None,
            "shared": psutil.virtual_memory().shared if hasattr(psutil.virtual_memory(), 'shared') else None
        },
        'network_connections': {
            conn.pid: {
                'fd': conn.fd,
                'family': conn.family,
                'type': conn.type,
                'laddr': {
                    "ip": conn.laddr.ip,
                    "port": conn.laddr.port
                },
                'raddr': conn.raddr,
                'status': conn.status,
            } for conn in psutil.net_connections()
            if conn.pid is not None  # Filter out connections with no associated PID
        },
        'network_io': {
            interface: {
                "bytes_sent": counters.bytes_sent,
                "bytes_recv": counters.bytes_recv,
                "packets_sent": counters.packets_sent,
                "packets_recv": counters.packets_recv,
                "errin": counters.errin,
                "errout": counters.errout,
                "dropin": counters.dropin,
                "dropout": counters.dropout
            } for interface, counters in psutil.net_io_counters(pernic=True).items()
        },
        'network_interfaces': {
            interface: psutil.net_if_addrs()[interface] for interface in psutil.net_if_addrs()
        },
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "version": platform.version(),
            "python": platform.python_version(),
            # "java": platform.java_ver(),
            "release": platform.release(),
            'kernel_version': platform.uname().release
        },
        'processes': {
            proc.name(): {
                'pid': proc.pid,
                'cpu_percent': proc.cpu_percent(),
                'memory_percent': proc.memory_percent(),
                'status': proc.status(),
                'create_time': proc.create_time()
            } for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status', 'create_time'])
        },
        'swap (bytes)': {
            "total": psutil.swap_memory().total,
            "used": psutil.swap_memory().used,
            "free": psutil.swap_memory().free,
            "percent": psutil.swap_memory().percent,
            "sin": psutil.swap_memory().sin,
            "sout": psutil.swap_memory().sout
        },
        'temps': psutil.sensors_temperatures(fahrenheit=True),
        "time": {
            "up": f"{timedelta(seconds=int(time.time() - psutil.boot_time()))}",
            "boot": datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S"),
        },
        'users': {
                user[0]: {
                    "terminal": user[1],
                    "host": user[2],
                    "started": f"{timedelta(seconds=int(time.time() - user[3]))} ago"
                } for user in psutil.users()
        },
    }


app = Flask(__name__)


@app.route('/', methods=['GET'])
def get_psutil():
    return jsonify(psutil_stats())


if __name__ == '__main__':
    app.run(debug=True)