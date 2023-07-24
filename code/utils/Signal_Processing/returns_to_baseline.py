def returns_to_baseline(previous_avg, tac_list_current, index, change_downward, range=120):
    back_index = (len(tac_list_current) - 1) if (index + range) > (len(tac_list_current) - 1) else (index + range)
    if not change_downward:
        return any([(tac < previous_avg) for tac in tac_list_current[index:back_index]])
    else:
        return any([(tac > previous_avg) for tac in tac_list_current[index:back_index]])