from flask import Flask, jsonify
import platform
import psutil
from datetime import datetime, timedelta
import time
import cpuinfo
import docker
from docker.errors import APIError


def get_docker_container_info():
    try:
        client = docker.from_env()  # Initialize Docker client from environment
        container_info = []

        # Iterate over all containers
        for container in client.containers.list():
            info = {
                'id': container.id,
                'name': container.name,
                'image': container.image.tags[0] if container.image.tags else 'N/A',
                'status': container.status,
                'ports': container.ports,
                'created': container.attrs['Created'],
                'cpu_usage': container.stats(stream=False)['cpu_stats']['cpu_usage']['total_usage'] / 1e9,
                'memory_usage': container.stats(stream=False)['memory_stats']['usage'],
                'network': container.attrs['NetworkSettings']['Networks'],
            }
            container_info.append(info)

        return container_info

    except docker.errors.APIError as e:
        print(f"Error accessing Docker API: {e}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


#TODO Get tuples from _common.py
def psutil_stats():
    return {
        # "fans": psutil.sensors_fans(),

        'cpu': {
            "cores": psutil.cpu_count(),
            'load_average (min : %)': {
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
            'processes': {
                proc.name(): {
                    'pid': proc.pid,
                    'cpu_percent': proc.cpu_percent(),
                    'memory_percent': proc.memory_percent(),
                    'status': proc.status(),
                    'create_time': proc.create_time()
                } for proc in
                psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status', 'create_time'])
            },
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
        "disk": {
            'io': {
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
        },
        "docker": {
            container["name"]: container for container in get_docker_container_info()
        },
        "kubernetes": {}, #todo
        "vm": {}, #todo
        "memory": {
            'ram (gb)': {  # todo in b Mb Gb?
                "total": round(psutil.virtual_memory().total / (1024 ** 3), 2),
                "available": round(psutil.virtual_memory().available / (1024 ** 3), 2),
                "percent": psutil.virtual_memory().percent,
                "used": round(psutil.virtual_memory().used / (1024 ** 3), 2),
                "free": round(psutil.virtual_memory().free / (1024 ** 3), 2),
                "active": round(psutil.virtual_memory().active / (1024 ** 3), 2) if hasattr(psutil.virtual_memory(), 'active') else None,
                "inactive": round(psutil.virtual_memory().inactive / (1024 ** 3), 2) if hasattr(psutil.virtual_memory(), 'inactive') else None,
                "buffers": round(psutil.virtual_memory().buffers / (1024 ** 3), 2) if hasattr(psutil.virtual_memory(), 'buffers') else None,
                "cached": round(psutil.virtual_memory().cached / (1024 ** 3), 2) if hasattr(psutil.virtual_memory(), 'cached') else None,
                "wired": round(psutil.virtual_memory().wired / (1024 ** 3), 2) if hasattr(psutil.virtual_memory(), 'wired') else None,
                "shared": round(psutil.virtual_memory().shared / (1024 ** 3), 2) if hasattr(psutil.virtual_memory(), 'shared') else None
            },
            'swap (bytes)': {
                "total": psutil.swap_memory().total,
                "used": psutil.swap_memory().used,
                "free": psutil.swap_memory().free,
                "percent": psutil.swap_memory().percent,
                "sin": psutil.swap_memory().sin,
                "sout": psutil.swap_memory().sout
            },
        },
        "network": {
            'connections': {
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
            'io': {
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
            "interfaces": {
                interface: {
                    'family': label.family,
                    'address': label.address,
                    'netmask': label.netmask,
                    'broadcast': label.broadcast,
                    'ptp': label.ptp
                } for interface, labels in psutil.net_if_addrs().items() for label in labels
            },
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


# todo
# voltage
# go alerts
# temps
# kubernetes



app = Flask(__name__)


@app.route('/', methods=['GET'])
def get_psutil():
    return jsonify(psutil_stats())


if __name__ == '__main__':
    app.run(debug=True)