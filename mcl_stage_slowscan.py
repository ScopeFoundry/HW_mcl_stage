from __future__ import division, print_function
import numpy as np
from ScopeFoundry.scanning import BaseRaster2DSlowScan
from ScopeFoundry import Measurement, LQRange
import time

class MCLStage2DSlowScan(BaseRaster2DSlowScan):
    
    name = "MCLStage2DSlowScan"
    def __init__(self, app):
        BaseRaster2DSlowScan.__init__(self, app, h_limits=(0,75), v_limits=(0,75), h_unit="um", v_unit="um")        
    
    def setup(self):
        BaseRaster2DSlowScan.setup(self)
        #Hardware
        self.stage = self.app.hardware.mcl_xyz_stage

    def move_position_start(self, x,y):
        #self.stage.y_position.update_value(x)
        #self.stage.y_position.update_value(y)
        self.stage.move_pos_slow(x,y,None)
        self.stage.settings.x_position.read_from_hardware()
        self.stage.settings.y_position.read_from_hardware()
    
    def move_position_slow(self, x,y, dx,dy):
        #self.stage.y_position.update_value(y)
        self.stage.move_pos_slow(x,y,None)
        self.stage.settings.x_position.read_from_hardware()
        self.stage.settings.y_position.read_from_hardware()

    def move_position_fast(self, x,y, dx,dy):
        #self.stage.x_position.update_value(x)
        self.stage.move_pos_fast(x, y, None)
        #self.current_stage_pos_arrow.setPos(x, y)
        #self.stage.settings.x_position.read_from_hardware()
        #self.stage.settings.y_position.read_from_hardware()
    
    