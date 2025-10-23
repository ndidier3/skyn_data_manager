from .Stats.statModel import statModel import pandas as pd

class dayQualityStats():
  def __init__(self, day_quality_metrics):
    self.event_features = day_quality_metrics
    self.statModel = statModel(day_quality_metrics)
    self.stat_frames = []
  
  # get non_wear stats by subid

  # amount of time 


