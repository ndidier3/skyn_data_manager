

class skynDay:
  def __init__(self, dataset, starting_index, ending_index):
    self.day_dataset = dataset.loc[starting_index:ending_index]

    self.begin_day = self.day_dataset['datetime'].iloc[0] if not self.day_dataset.empty else None
    self.end_day = self.day_dataset['datetime'].iloc[-1] if not self.day_dataset.empty else None

    self.device_turned_on_duration = self.day_dataset['device_turned_on'].sum() / 60
    self.device_turned_on_percentage_of_day = self.device_turned_on_duration / 24

    """
    device_worn_duration will always be equal or less than device_turned_on_duration.
    This is because values for device_worn is null whenever device is not turned on.
    Therefore, device_worn_duration will be the duration when device is turned on AND worn.
    """
    self.device_worn_duration = self.day_dataset['device_worn'].sum() / 60
    self.device_turned_on_percentage_of_device_on = self.device_worn_duration / self.device_turned_on_duration
    self.device_worn_percentage_of_day = self.device_worn_duration / 24




    

  
               
