package ACS_Behavior_Model {
    
    // Abstract base definition of our constraint properties
    doc /* 
     * The SafeACS Digital Twin behavior model. 
     * This establishes the deterministic boundaries used to generate 
     * the runtime Pydantic guardrails at the edge.
     */

    // Define the behavioral states
    enum def ACS_State {
        Nominal;
        Anomaly_Drift;
        Fatal_Fault;
        Safe_Mode;
    }

    // Define the physical context and hardware boundaries
    part def AttitudeControlSystem {
        
        // Structural Constraints (Zero-Drift mappings to edge Pydantic limits)
        attribute rw_rpm_limit : Real = 6000.0;
        attribute rw_anomaly_threshold : Real = 3000.0;
        
        // Dynamic Telemetry Values
        attribute current_max_rpm : Real;
        attribute active_state : ACS_State;
        
        // State Machine defining transition guard behaviors
        state machine behavior {
            in Nominal;
            
            transition t1
                first Nominal
                accept timeEvent
                guard current_max_rpm > rw_anomaly_threshold and current_max_rpm <= rw_rpm_limit
                then Anomaly_Drift;
                
            transition t2
                first Anomaly_Drift
                accept timeEvent
                guard current_max_rpm > rw_rpm_limit
                then Fatal_Fault;
                
            transition t3
                first Nominal
                accept timeEvent
                guard current_max_rpm > rw_rpm_limit
                then Fatal_Fault;
                
            transition t4
                first Fatal_Fault
                accept timeEvent
                then Safe_Mode; // Irreversible hard-fault boundary reached
                
            transition t5
                first Safe_Mode
                accept timeEvent
                guard current_max_rpm <= rw_anomaly_threshold
                then Nominal; // Recovery sequence complete
        }
    }
}
