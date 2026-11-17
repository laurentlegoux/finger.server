import sys, time, gc  
from mpos import BuildInfo, DeviceInfo  
  
print("MicroPythonOS %s (API %s)" % (BuildInfo.version.release,  
                                     BuildInfo.version.api_level))  
print("Hardware: %s" % DeviceInfo.hardware_id)  
print("Platform: %s" % sys.platform)  
print("Memory: %d free / %d total" % (gc.mem_free(),  
                                      gc.mem_free() + gc.mem_alloc()))  
try:  
    from mpos import WifiService  
    print("IPv4: %s" % (WifiService.get_ipv4_address() or "n/a"))  
except Exception:  
    pass  
if sys.platform == "esp32":  
    try:  
        import machine  
        mac = ':'.join('%02X' % b for b in machine.unique_id())  
        print("MAC: %s  freq: %s" % (mac, machine.freq()))  
    except Exception:  
        pass  
try:  
    import shutil  
    u = shutil.disk_usage('/')  
    print("Disk /: %d free / %d total" % (u.free, u.total))  
except Exception:  
    pass  
print("Uptime: %ds" % (time.ticks_ms() // 1000))