# Pan-Tilt Camera Experiments

This folder contains a shared tracker implementation and five experiment entry files.

## Install dependencies

```bash
pip install opencv-python mediapipe pyserial
```

## Run experiments

V0 only observes raw detection signal. It does not use Arduino.

```bash
python run_v0_detection_only.py
```

V1 observes raw vs smoothed signal. It does not use Arduino.

```bash
python run_v1_detection_with_smoothing.py
```

V2 starts P control without smoothing.

```bash
python run_v2_p_control_no_smoothing.py
```

V3 uses P control with smoothing.

```bash
python run_v3_p_control_with_smoothing.py
```

V4 uses PD control with smoothing.

```bash
python run_v4_pd_control_with_smoothing.py
```

Press `q` to stop a run.

Each run writes:

- `logs/<run_id>.csv`
- `logs/<run_id>_meta.json`

## Experiment sequence

1. `v0_detection_only`: no control, no smoothing
2. `v1_detection_with_smoothing`: no control, with smoothing
3. `v2_p_control_no_smoothing`: P control, no smoothing
4. `v3_p_control_with_smoothing`: P control, with smoothing
5. `v4_pd_control_with_smoothing`: PD control, with smoothing
