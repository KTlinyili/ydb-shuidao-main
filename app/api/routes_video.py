from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import uuid
import os
import time
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/vision", tags=["video"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage", "uploads")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage", "outputs")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

_jobs: dict = {}


@router.post("/video")
async def upload_video(
    file: UploadFile = File(...),
    model_id: Optional[str] = Form(default="best_cls"),
    confidence_threshold: float = Form(default=0.5),
    save_record: bool = Form(default=True),
):
    job_id = str(uuid.uuid4())[:8]
    upload_path = os.path.join(UPLOAD_DIR, f"{job_id}_{file.filename}")
    with open(upload_path, "wb") as f:
        content = await file.read()
        f.write(content)

    _jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "progress": 0,
        "processed_frames": 0,
        "total_frames": 0,
        "current_fps": 0,
        "avg_inference_ms": 0,
        "class_counts": {},
        "keyframes": [],
        "output_video_url": None,
        "error": None,
        "created_at": time.time(),
        "upload_path": upload_path,
        "model_id": model_id,
        "confidence_threshold": confidence_threshold,
    }

    asyncio.create_task(_process_video(job_id))
    return {"job_id": job_id, "status": "queued", "message": "Video uploaded, processing started"}


async def _process_video(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        return

    job["status"] = "running"
    upload_path = job["upload_path"]
    model_id = job.get("model_id", "best_cls")
    conf_threshold = job.get("confidence_threshold", 0.5)

    try:
        import cv2

        if model_id.startswith("best_cls") or "cls" in model_id:
            from ultralytics import YOLO
            model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "best_cls.pt")
            task_type = "classify"
        else:
            from ultralytics import YOLO
            model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "best.pt")
            task_type = "detect"

        if not os.path.exists(model_path):
            job["status"] = "failed"
            job["error"] = f"Model file not found: {model_path}"
            return

        model = YOLO(model_path)

        cap = cv2.VideoCapture(upload_path)
        if not cap.isOpened():
            job["status"] = "failed"
            job["error"] = "Cannot open video file"
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        job["total_frames"] = total_frames

        output_path = os.path.join(OUTPUT_DIR, f"{job_id}_annotated.mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        class_counts = {}
        keyframes = []
        total_inference_ms = 0
        processed = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            t0 = time.time()
            results = model.predict(frame, imgsz=224 if task_type == "classify" else 640, verbose=False)
            inference_ms = (time.time() - t0) * 1000
            total_inference_ms += inference_ms

            if task_type == "classify":
                top1 = int(results[0].probs.top1)
                top1_conf = float(results[0].probs.top1conf)
                class_name = results[0].names[top1]
                class_counts[class_name] = class_counts.get(class_name, 0) + 1

                if top1_conf >= conf_threshold:
                    label = f"{class_name} {top1_conf:.2f}"
                    cv2.putText(frame, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    cv2.putText(frame, f"FPS: {fps:.0f}  Inference: {inference_ms:.0f}ms",
                                (10, height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)

                    if top1_conf >= 0.9 and len(keyframes) < 10:
                        keyframe_path = os.path.join(OUTPUT_DIR, f"{job_id}_keyframe_{len(keyframes)}.jpg")
                        cv2.imwrite(keyframe_path, frame)
                        keyframes.append({
                            "frame": processed,
                            "class": class_name,
                            "confidence": top1_conf,
                            "url": f"/api/v1/vision/keyframe/{job_id}/{len(keyframes)-1}",
                        })
            else:
                boxes = results[0].boxes
                if boxes is not None:
                    for box in boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        conf = float(box.conf[0])
                        cls = int(box.cls[0])
                        class_name = results[0].names[cls]
                        class_counts[class_name] = class_counts.get(class_name, 0) + 1

                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        label = f"{class_name} {conf:.2f}"
                        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                    cv2.putText(frame, f"FPS: {fps:.0f}  Inference: {inference_ms:.0f}ms",
                                (10, height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)

            out.write(frame)
            processed += 1

            if processed % 5 == 0:
                job["processed_frames"] = processed
                job["progress"] = round(processed / total_frames * 100, 1) if total_frames > 0 else 0
                job["avg_inference_ms"] = round(total_inference_ms / processed, 1)
                job["class_counts"] = class_counts
                job["keyframes"] = keyframes
                await asyncio.sleep(0.01)

        cap.release()
        out.release()

        job["status"] = "completed"
        job["progress"] = 100
        job["processed_frames"] = processed
        job["total_frames"] = total_frames
        job["avg_inference_ms"] = round(total_inference_ms / processed, 1) if processed > 0 else 0
        job["current_fps"] = round(fps, 1)
        job["class_counts"] = class_counts
        job["keyframes"] = keyframes
        job["output_video_url"] = f"/api/v1/vision/download/{job_id}"

        logger.info(f"Video {job_id} processed: {processed} frames, {class_counts}")

    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        logger.error(f"Video processing failed for {job_id}: {e}")


@router.get("/video/{job_id}")
async def get_video_status(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "progress": job["progress"],
        "processed_frames": job["processed_frames"],
        "total_frames": job["total_frames"],
        "current_fps": job["current_fps"],
        "avg_inference_ms": job["avg_inference_ms"],
        "class_counts": job["class_counts"],
        "keyframes": job["keyframes"],
        "output_video_url": job["output_video_url"],
        "error": job["error"],
    }


@router.get("/download/{job_id}")
async def download_video(job_id: str):
    from fastapi.responses import FileResponse
    job = _jobs.get(job_id)
    if not job or job["status"] != "completed":
        raise HTTPException(status_code=404, detail="Video not ready")
    output_path = os.path.join(OUTPUT_DIR, f"{job_id}_annotated.mp4")
    if not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="Output file not found")
    return FileResponse(output_path, media_type="video/mp4", filename=f"annotated_{job_id}.mp4")
