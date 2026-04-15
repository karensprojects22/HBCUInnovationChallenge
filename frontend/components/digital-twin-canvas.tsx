"use client";

import { useEffect, useRef } from "react";

type Keypoint = [number, number, number] | null;

export type PoseKeypoints = {
  left_shoulder?: Keypoint;
  right_shoulder?: Keypoint;
  left_hip?: Keypoint;
  right_hip?: Keypoint;
  left_knee?: Keypoint;
  right_knee?: Keypoint;
  left_ankle?: Keypoint;
  right_ankle?: Keypoint;
};

type PoseFrame = {
  frame: number;
  timestamp: number;
  keypoints: PoseKeypoints;
};

type FrameAnalysis = {
  frame: number;
  rep: number;
  risk_score: number;
};

type Props = {
  poseFrames: PoseFrame[];
  frameData: FrameAnalysis[];
  width?: number;
  height?: number;
  sourceWidth?: number;
  sourceHeight?: number;
  focusJoint: string;
};

const BONES: Array<[keyof PoseKeypoints | "neck" | "head", keyof PoseKeypoints | "neck" | "head"]> = [
  ["head", "neck"],
  ["neck", "left_shoulder"],
  ["neck", "right_shoulder"],
  ["left_shoulder", "left_hip"],
  ["right_shoulder", "right_hip"],
  ["left_hip", "right_hip"],
  ["left_hip", "left_knee"],
  ["left_knee", "left_ankle"],
  ["right_hip", "right_knee"],
  ["right_knee", "right_ankle"]
];

function riskColor(score: number) {
  if (score >= 65) return "#fb7185";
  if (score >= 40) return "#fbbf24";
  return "#34d399";
}

function scalePoint(point: Keypoint, width: number, height: number, sourceWidth: number, sourceHeight: number) {
  if (!point) return null;
  return [(point[0] / sourceWidth) * width, (point[1] / sourceHeight) * height] as const;
}

export function DigitalTwinCanvas({
  poseFrames,
  frameData,
  width = 420,
  height = 480,
  sourceWidth = 720,
  sourceHeight = 1280,
  focusJoint
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const frameRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !poseFrames.length || !frameData.length) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationId = 0;
    let lastFrameTime = 0;
    frameRef.current = 0;

    const draw = (timestamp: number) => {
      if (timestamp - lastFrameTime > 90) {
        lastFrameTime = timestamp;
        frameRef.current = (frameRef.current + 1) % Math.min(poseFrames.length, frameData.length);
      }

      const poseFrame = poseFrames[frameRef.current];
      const analysis = frameData[frameRef.current];
      const accent = riskColor(analysis.risk_score);

      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = "#030712";
      ctx.fillRect(0, 0, width, height);

      const joints = {
        left_shoulder: scalePoint(poseFrame.keypoints.left_shoulder ?? null, width, height, sourceWidth, sourceHeight),
        right_shoulder: scalePoint(poseFrame.keypoints.right_shoulder ?? null, width, height, sourceWidth, sourceHeight),
        left_hip: scalePoint(poseFrame.keypoints.left_hip ?? null, width, height, sourceWidth, sourceHeight),
        right_hip: scalePoint(poseFrame.keypoints.right_hip ?? null, width, height, sourceWidth, sourceHeight),
        left_knee: scalePoint(poseFrame.keypoints.left_knee ?? null, width, height, sourceWidth, sourceHeight),
        right_knee: scalePoint(poseFrame.keypoints.right_knee ?? null, width, height, sourceWidth, sourceHeight),
        left_ankle: scalePoint(poseFrame.keypoints.left_ankle ?? null, width, height, sourceWidth, sourceHeight),
        right_ankle: scalePoint(poseFrame.keypoints.right_ankle ?? null, width, height, sourceWidth, sourceHeight)
      };

      const neck =
        joints.left_shoulder && joints.right_shoulder
          ? [
              (joints.left_shoulder[0] + joints.right_shoulder[0]) / 2,
              (joints.left_shoulder[1] + joints.right_shoulder[1]) / 2 - 8
            ]
          : [width / 2, height * 0.22];
      const head = [neck[0], neck[1] - 30] as const;

      const torsoTopLeft = joints.left_shoulder ?? [width * 0.4, height * 0.3];
      const torsoTopRight = joints.right_shoulder ?? [width * 0.6, height * 0.3];
      const torsoBottomRight = joints.right_hip ?? [width * 0.56, height * 0.56];
      const torsoBottomLeft = joints.left_hip ?? [width * 0.44, height * 0.56];

      ctx.beginPath();
      ctx.moveTo(torsoTopLeft[0], torsoTopLeft[1]);
      ctx.lineTo(torsoTopRight[0], torsoTopRight[1]);
      ctx.lineTo(torsoBottomRight[0], torsoBottomRight[1]);
      ctx.lineTo(torsoBottomLeft[0], torsoBottomLeft[1]);
      ctx.closePath();
      ctx.fillStyle = "rgba(56, 189, 248, 0.14)";
      ctx.fill();
      ctx.strokeStyle = "rgba(125, 211, 252, 0.45)";
      ctx.lineWidth = 1.5;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(head[0], head[1], 18, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(239, 246, 255, 0.08)";
      ctx.fill();
      ctx.strokeStyle = accent;
      ctx.lineWidth = 2.5;
      ctx.stroke();

      const renderJoints = {
        ...joints,
        neck,
        head
      } as Record<string, readonly [number, number] | null>;

      BONES.forEach(([start, end]) => {
        const startPoint = renderJoints[start];
        const endPoint = renderJoints[end];
        if (!startPoint || !endPoint) return;
        ctx.beginPath();
        ctx.moveTo(startPoint[0], startPoint[1]);
        ctx.lineTo(endPoint[0], endPoint[1]);
        ctx.strokeStyle = accent;
        ctx.lineWidth = end.includes("ankle") ? 7 : 9;
        ctx.lineCap = "round";
        ctx.stroke();
      });

      Object.entries(renderJoints).forEach(([name, point]) => {
        if (!point) return;
        const highlight =
          focusJoint !== "full_lower_body" &&
          name.includes(focusJoint.replace("_joint", "").replace("_focus", "").split("_")[0]);
        ctx.beginPath();
        ctx.arc(point[0], point[1], highlight ? 8 : 5, 0, Math.PI * 2);
        ctx.fillStyle = highlight ? "#fbbf24" : accent;
        ctx.shadowBlur = highlight ? 18 : 0;
        ctx.shadowColor = highlight ? "#fbbf24" : "transparent";
        ctx.fill();
        ctx.shadowBlur = 0;
      });

      ctx.fillStyle = "#e2e8f0";
      ctx.font = "600 13px Inter, sans-serif";
      ctx.textAlign = "left";
      ctx.fillText("ATHLETIQ Digital Twin", 18, 28);
      ctx.fillStyle = accent;
      ctx.fillText(`Risk ${analysis.risk_score.toFixed(0)} | Rep ${analysis.rep}`, 18, height - 20);

      animationId = window.requestAnimationFrame(draw);
    };

    animationId = window.requestAnimationFrame(draw);
    return () => window.cancelAnimationFrame(animationId);
  }, [frameData, focusJoint, height, poseFrames, sourceHeight, sourceWidth, width]);

  return <canvas ref={canvasRef} width={width} height={height} className="digitalTwinCanvas" />;
}
