from __future__ import division, print_function
#import numpy as np
from ScopeFoundry.scanning import BaseRaster2DSlowScan, BaseRaster2DFrameSlowScan
#from ScopeFoundry import Measurement, LQRange
import time

class MCLStage2DSlowScan(BaseRaster2DSlowScan):
    
    name = "MCLStage2DSlowScan"
    def __init__(self, app):
        BaseRaster2DSlowScan.__init__(self, app, h_limits=(1,74), v_limits=(1,74),
                                      h_spinbox_step = 0.1, v_spinbox_step=0.1,
                                      h_unit="um", v_unit="um")        
    
    def setup(self):
        BaseRaster2DSlowScan.setup(self)
        
        self.settings.New("h_axis", initial="X", dtype=str, choices=("X", "Y", "Z"))
        self.settings.New("v_axis", initial="Y", dtype=str, choices=("X", "Y", "Z"))
        
        self.ax_map = dict(X=0, Y=1, Z=2)
        #Hardware
        self.stage = self.app.hardware.mcl_xyz_stage
        
        self.settings.h_axis.add_listener(self.on_new_stage_limits)
        self.settings.v_axis.add_listener(self.on_new_stage_limits)
        self.stage.settings.x_max.add_listener(self.on_new_stage_limits)
        
    def on_new_stage_limits(self):
        h_axis = self.settings['h_axis'].lower()
        v_axis = self.settings['v_axis'].lower()
        h_max = self.stage.settings[h_axis + '_max']
        v_max = self.stage.settings[v_axis + '_max']
        
        self.set_h_limits(0.1, h_max-0.1)
        self.set_v_limits(0.1, v_max-0.1)
        
        


        
    def setup_figure(self):
        BaseRaster2DSlowScan.setup_figure(self)
        self.set_details_widget(widget=self.settings.New_UI(include=['h_axis', 'v_axis']))
        

    def pre_scan_setup(self):
        BaseRaster2DSlowScan.pre_scan_setup(self)
        if hasattr(self.app.settings, 'open_shutter_before_scan'):
            if self.app.settings.open_shutter_before_scan.val:
                self.app.hardware.shutter_servo.settings['shutter_open'] = True
                time.sleep(0.5)
                
                
    def post_scan_cleanup(self):
        if hasattr(self.app.settings, 'close_shutter_after_scan'):
            if self.app.settings.close_shutter_after_scan.val:
                self.app.hardware.shutter_servo.settings['shutter_open'] = False  
            

        

    def move_position_start(self, h,v):
        #self.stage.y_position.update_value(x)
        #self.stage.y_position.update_value(y)
        
        S = self.settings
        
        coords = [None, None, None]
        coords[self.ax_map[S['h_axis']]] = h
        coords[self.ax_map[S['v_axis']]] = v
        
        #self.stage.move_pos_slow(x,y,None)
        self.stage.move_pos_slow(*coords)
        self.stage.settings.x_position.read_from_hardware()
        self.stage.settings.y_position.read_from_hardware()
        self.stage.settings.z_position.read_from_hardware()
    
    def move_position_slow(self, h,v, dh,dv):
        self.move_position_start(h, v)

    def move_position_fast(self,  h,v, dh,dv):
        #self.stage.x_position.update_value(x)
        S = self.settings        
        coords = [None, None, None]
        coords[self.ax_map[S['h_axis']]] = h
        coords[self.ax_map[S['v_axis']]] = v
        self.stage.move_pos_fast(*coords)
        #self.stage.move_pos_fast(x, y, None)
        #self.current_stage_pos_arrow.setPos(x, y)
        self.stage.settings.x_position.read_from_hardware()
        self.stage.settings.y_position.read_from_hardware()
        self.stage.settings.z_position.read_from_hardware()
        
    
class MCLStage2DFrameSlowScan(BaseRaster2DFrameSlowScan):
    
    name = "MCLStage2DFrameSlowScan"
    
    def __init__(self, app):
        BaseRaster2DFrameSlowScan.__init__(self, app, h_limits=(0,75), v_limits=(0,75), h_unit="um", v_unit="um")        
    
    def setup(self):
        MCLStage2DSlowScan.setup(self)

    def move_position_start(self, h,v):
        MCLStage2DSlowScan.move_position_start(self, h, v)
    
    def move_position_slow(self, h,v, dh,dv):
        MCLStage2DSlowScan.move_position_slow(self, h,v, dh,dv)
        
    def move_position_fast(self,  h,v, dh,dv):
        MCLStage2DSlowScan.move_position_fast(self,  h,v, dh,dv)
    
    def on_new_stage_limits(self):
        MCLStage2DSlowScan.on_new_stage_limits(self)
        
        
class MCLStage3DStackSlowScan(MCLStage2DFrameSlowScan):
    
    def setup(self):
        MCLStage2DFrameSlowScan.setup(self)
        
        self.settings.New("stack_axis", initial="Z", dtype=str, choices=("X", "Y", "Z"))
        self.settings.New_Range('stack', dtype=float)
        
        self.settings.stack_num.add_listener(self.settings.n_frames.update_value, int)
        
    def on_new_frame(self, frame_i):
        S = self.settings
        stack_range = S.ranges['stack']
        
        stack_pos_i = stack_range.array[frame_i]
        coords = [None, None, None]
        coords[self.ax_map[S['stack_axis']]] = stack_pos_i
        
        self.stage.move_pos_slow(*coords)
        self.stage.settings.x_position.read_from_hardware()
        self.stage.settings.y_position.read_from_hardware()
        self.stage.settings.z_position.read_from_hardware()
        


class Delay_MCL_2DSlowScan(MCLStage2DSlowScan):
    
    name = 'Delay_MCL_2DSlowScan'

    def setup_figure(self):
        MCLStage2DSlowScan.setup_figure(self)
        self.set_details_widget(widget=self.settings.New_UI(include=['h_axis', 'v_axis', 'pixel_time', 'frame_time']))


    def scan_specific_setup(self):
        #self.settings['pixel_time'] = 0.01
        self.settings.pixel_time.change_readonly(False)
        
    def collect_pixel(self, pixel_num, k, j, i):
        time.sleep(self.settings['pixel_time'])
        
    def post_scan_cleanup(self):
        pass
        
    def update_display(self):
        #MCLStage2DSlowScan.update_display(self)
        self.stage.settings.x_position.read_from_hardware()
        self.stage.settings.y_position.read_from_hardware()
        if self.stage.nanodrive.num_axes > 2:
            self.stage.settings.z_position.read_from_hardware()