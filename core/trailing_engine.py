class TrailingEngine:
    def __init__(self, commission=0.0056):
        self.commission = commission

    def calculate_new_levels(self, current_price, current_sl, current_tp, step_count, trailing_sl_pct, trailing_tp_pct):
        """
        Strategy D: Stepped Trailing.
        - Every time current_tp is hit, we reset the SL and TP relative to that hit price.
        - trailing_sl_pct: The % below the target where the NEW SL will be placed (e.g. 0.988 for 1.2% drop).
        - trailing_tp_pct: The % above the target where the NEW TP will be placed (e.g. 1.01 for 1% rise).
        """
        new_sl = current_sl
        new_tp = current_tp
        new_step = step_count
        updated = False
        
        # Check if we hit the current TP target
        if current_price >= current_tp:
            new_step += 1
            # The hit price becomes the new base
            base_price = current_tp 
            
            # Reset SL based on the Subida de Piso % (trailing_sl_pct)
            new_sl = base_price * trailing_sl_pct
            
            # Reset TP based on the Siguiente Escalón % (trailing_tp_pct)
            new_tp = base_price * trailing_tp_pct
            
            updated = True
            
        return {
            "updated": updated,
            "sl": new_sl,
            "tp": new_tp,
            "step": new_step
        }

    def check_exit(self, current_price, current_sl):
        """Check if we should exit based on SL."""
        if current_price <= current_sl:
            return True
        return False
