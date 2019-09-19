from __future__ import division, print_function, absolute_import
import ctypes
from ctypes import c_int, c_byte, c_ubyte, c_short, c_double, cdll, pointer, byref
import time
import numpy as np
import threading


### IMPORTANT NOTE: DLL's of the same MADLIB version can be different for different
###                 serial numbers of Nanodrives and cause subtle errors!
###                 thus using the local repo copy of the DLL is a bad idea,
###                 point directly the system installed DLL instead.

# previous version to use local copy of DLL
"""
import os
import platform

print(platform.architecture())

if platform.architecture()[0] == '64bit':
    madlib_path = os.path.abspath(
                    os.path.join(os.path.dirname(__file__),"mcl_64bit/MADLib.dll"))
else:
    madlib_path = os.path.abspath(
                    os.path.join(os.path.dirname(__file__),"MADLib.dll"))

    wdapilib_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__),"wdapi1010.dll"))
    wdapidll = cdll.LoadLibrary(wdapilib_path)
"""

# tested with 64bit windows
madlib_path = r"C:\Program Files\Mad City Labs\NanoDrive\madlib.dll"

print("loading DLL:", repr(madlib_path))

## Load DLL
madlib = cdll.LoadLibrary(madlib_path)

# set return types of certain function
madlib.MCL_SingleReadZ.restype = c_double
madlib.MCL_SingleReadN.restype = c_double
madlib.MCL_MonitorZ.restype = c_double
madlib.MCL_MonitorN.restype = c_double
madlib.MCL_ReadEncoderZ.restype = c_double

madlib.MCL_GetCalibration.restype = c_double
#more...
MCL_ERROR_CODES = {
   0: "MCL_SUCCESS",
   -1: "MCL_GENERAL_ERROR",
    -2: "MCL_DEV_ERROR",
    -3: "MCL_DEV_NOT_ATTACHED",
    -4: "MCL_USAGE_ERROR",
    -5: "MCL_DEV_NOT_READY",
    -6: "MCL_ARGUMENT_ERROR",
    -7: "MCL_INVALID_AXIS",
    -8: "MCL_INVALID_HANDLE"
}

SLOW_STEP_PERIOD = 0.050  #units are seconds

class MCLProductInformation(ctypes.Structure):
    _fields_ = [
        ("axis_bitmap",     c_byte),    #//bitmap of available axis
        ("ADC_resolution",  c_short), #//# of bits of resolution
        #("pad", c_byte),
        ("DAC_resolution",  c_short), #//# of bits of resolution
        ("Product_id",      c_short),   
        ("FirmwareVersion", c_short),
        ("FirmwareProfile", c_short),]
        
    _pack_ = 1 # important for field alignment
    
    def print_info(self):
        print("MCL Product Information")
        for fieldname, fieldtype in self._fields_:
            fieldval = self.__getattribute__(fieldname)
            print("\t", fieldname, "\t\t", fieldval, "\t\t", bin(fieldval))
        
        

class MCLNanoDrive(object):

    def __init__(self, debug=False):
        
        self.lock = threading.Lock()
        
        self.debug = debug
        
        self.MCL_ERROR_CODES = MCL_ERROR_CODES
        
        ver = c_short()
        rev = c_short()
        madlib.MCL_DLLVersion(byref(ver), byref(rev))
        if self.debug:
            print("MCL_DLLVersion", ver.value, rev.value)
            print("madlib.MCL_CorrectDriverVersion():", madlib.MCL_CorrectDriverVersion())
        if not madlib.MCL_CorrectDriverVersion():
            print("MCL_CorrectDriverVersion is False")
        
        handle = self._handle = madlib.MCL_InitHandle()
        assert handle > 0

        dev_attached = madlib.MCL_DeviceAttached(2000, handle)
        print("dev_attached", dev_attached)

        if self.debug: print("handle:", hex(handle))

        if not handle:
            print("MCLNanoDrive failed to grab device handle ", hex(handle))

        self.prodinfo = MCLProductInformation()
        madlib.MCL_GetProductInfo(byref(self.prodinfo), handle)
        
        if self.debug: self.prodinfo.print_info()
        
        self.device_serial_number = madlib.MCL_GetSerialNumber(handle)
        if self.debug: print("MCL_GetSerialNumber", self.device_serial_number)
        
        self.cal_X = None
        self.cal_Y = None
        self.cal_Z = None
        
        self.num_axes = 0
    
        self.cal = dict()
        for axname, axnum, axbitmap in [('X', 1, 0b001), ('Y', 2, 0b010), ('Z', 3, 0b100)]:
            axvalid = bool(self.prodinfo.axis_bitmap & axbitmap)
            if debug: print(axname, axnum, "axbitmap:", bin(axbitmap), "axvalid", axvalid)
            
            if not axvalid:
                if debug: print("No %s axis, skipping" % axname)
                continue
            
            self.num_axes += 1
            
            cal = madlib.MCL_GetCalibration(axnum, handle)

            setattr(self, 'cal_%s' % axname, cal)
            self.cal[axnum] = cal
            if debug: print("cal_%s: %g" % (axname, cal))
        
        self.set_max_speed(100)  # default speed for slow movement is 100 microns/second
        #self.get_pos()
        
        self.lock 

    def set_max_speed(self, max_speed):
        '''
        Units are in microns/second
        '''
        self.max_speed = float(max_speed)
    
    def get_max_speed(self):
        return self.max_speed
    
    def set_pos_slow(self, x=None, y=None, z=None):
        '''
        x -> axis 1
        y -> axis 2
        z -> axis 3
        '''
        
        x_start, y_start, z_start = self.get_pos()
        
        if x is not None:
            dx = x - x_start
        else:
            dx = 0
        if y is not None:            
            dy = y - y_start
        else:
            dy = 0
        if z is not None:
            dz = z-z_start
        else:
            dz = 0
        
        # Compute the amount of time that will be needed to make the movement.
        dt = np.sqrt(dx**2 + dy**2 + dz**2)/self.max_speed
            
        # Assume dt is in ms; divide the movement into SLOW_STEP_PERIOD chunks
        steps = int( np.ceil(dt/SLOW_STEP_PERIOD))
        x_step = dx/steps
        y_step = dy/steps
        z_step = dz/steps
        

        
        for i in range(1,steps+1):
            t1 = time.time()
            if z is not None:
                self.set_pos(x_start+i*x_step, y_start+i*y_step, z_start+i*z_step)
            else:
                self.set_pos(x_start+i*x_step, y_start+i*y_step, None)
            t2 = time.time()
            
            if (t2-t1) < SLOW_STEP_PERIOD:
                time.sleep(SLOW_STEP_PERIOD - (t2-t1))
        
        # Update internal variables with current position
        self.get_pos()
        
        
        
        
    def __del__(self):
        self.close()
        
    def close(self):
        madlib.MCL_ReleaseHandle(self._handle)
        
    def move_rel(self, dx, dy, dz=0):
        pass
        #TODO

    def set_pos(self, x=None, y=None, z=None):
        if x is not None:
            assert 0 <= x <= self.cal_X
            self.set_pos_ax(x, 1)
        if y is not None:
            assert 0 <= y <= self.cal_Y
            self.set_pos_ax(y, 2)
        if z is not None:
            assert 0 <= z <= self.cal_Z
            self.set_pos_ax(z, 3)
        
        #madlib.MCL_DeviceAttached(200, self._handle)
        # MCL_DeviceAttached can be used as a simple wait function. In this case
        # it is being used to allow the nanopositioner to finish its motion before 
        # reading its position. (standard 200)
        #madlib.MCL_DeviceAttached(100, self._handle)
        
    def set_pos_ax(self, pos, axis):
        if self.debug: print("set_pos_ax ", pos, axis)
        assert 1 <= axis <= self.num_axes
        assert 0 <= pos <= self.cal[axis]
        self.handle_err(madlib.MCL_SingleWriteN(c_double(pos), axis, self._handle))
        
    
    def get_pos_ax(self, axis):
        pos = float(self.singleReadN(axis))
        if self.debug: print("get_pos_ax", axis, pos)
        return pos
    
    def get_pos(self):
        self.x_pos = self.singleReadN(1)
        self.y_pos = self.singleReadN(2)
        if self.num_axes > 2:
            self.z_pos = self.singleReadN(3)
        else:
            self.z_pos = -1
            
        return (self.x_pos, self.y_pos, self.z_pos)
    
    def singleReadN(self, axis):
        with self.lock:
            resp = madlib.MCL_SingleReadN(axis, self._handle)
        if resp < 0 and resp in self.MCL_ERROR_CODES:
            raise IOError("MCL singleReadN Error: {}".format(self.MCL_ERROR_CODES[resp]))
            #print('singleReadN', self.MCL_ERROR_CODES[resp])
        return resp
    
    def monitorN(self, pos, axis):
        with self.lock:
            resp = madlib.MCL_MonitorN(pos, axis, self._handle)
        if resp < 0 and resp in self.MCL_ERROR_CODES:
            #raise IOError(self.MCL_ERROR_CODES[resp])
            print('monitorN', pos, axis, self.MCL_ERROR_CODES[resp])        
        return resp
    
    def getCommandedPosition(self):
        xCom = c_double()
        yCom = c_double()
        zCom = c_double()
        resp = madlib.MCL_GetCommandedPosition(byref(xCom), byref(yCom), byref(zCom), self._handle)
        if resp < 0:
            #raise IOError(self.MCL_ERROR_CODES[resp])
            print('getCommandedPosition',  self.MCL_ERROR_CODES[resp])        
        return xCom.value, yCom.value, zCom.value
        
    
    def set_pos_ax_slow(self, pos, axis):
        if self.debug: print("set_pos_slow_ax ", pos, axis)
        assert 1 <= axis <= self.num_axes
        #assert 0 <= pos <= self.cal[axis]
        pos = np.clip(pos, 0, self.cal[axis])
        
        start = self.get_pos_ax(axis)
        
        dl = pos - start
        dt = abs(dl) / self.max_speed
        
        # Assume dt is in ms; divide the movement into SLOW_STEP_PERIOD chunks
        steps = int(np.ceil(dt/SLOW_STEP_PERIOD))
        l_step = dl/steps
        
        print("\t", steps, l_step, dl, dt, start)        
        
        for i in range(1,steps+1):
            t1 = time.time()         
            self.set_pos_ax(start+i*l_step, axis)
            t2 = time.time()
            
            if (t2-t1) < SLOW_STEP_PERIOD:
                time.sleep(SLOW_STEP_PERIOD - (t2-t1))
        # Update internal variables with current position
        self.get_pos()
        
    def handle_err(self, retcode):
        if retcode < 0:
            raise IOError(self.MCL_ERROR_CODES[retcode])
        return retcode
        
if __name__ == '__main__':
    print("MCL nanodrive test")
    
    nanodrive = MCLNanoDrive(debug=True)
    print(nanodrive.getCommandedPosition())
    #print nanodrive.monitorN(0, 1)
    
    #for x,y in [ (0,0), (10,10), (30,30), (50,50), (50,25), (50,0)]:
    """for x,y in [ (30,0), (30,10), (30,30), (30,50), (30,25), (30,0)]:
        print "moving to ", x,y
        nanodrive.set_pos(x,y)
        x1,y1,z = nanodrive.get_pos()
        print "moved to ", x1, y1,z
        time.sleep(1)"""
    
    nanodrive.close()
    
