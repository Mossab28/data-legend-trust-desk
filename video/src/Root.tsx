import React from "react";
import { Composition, Series } from "remotion";
import {
  S1Hook,
  S2Problem,
  S3Verdicts,
  S4Receipts,
  S5Validator,
  S6Deserts,
  S7Override,
  S8Close,
} from "./scenes";
import { LiveDemo } from "./LiveDemo";

const FPS = 30;
const OVERLAP = 16; // frames of zoom-through crossfade between scenes

// Scene durations in frames (30 fps).
const T = {
  s1: 150,
  s2: 200,
  s3: 240,
  s4: 210,
  s5: 230,
  s6: 230,
  s7: 230,
  s8: 210,
};

const TOTAL =
  Object.values(T).reduce((a, b) => a + b, 0) -
  OVERLAP * (Object.keys(T).length - 1);

const Video: React.FC = () => (
  <>
    <Series>
      <Series.Sequence durationInFrames={T.s1}>
        <S1Hook durationInFrames={T.s1} />
      </Series.Sequence>
      <Series.Sequence durationInFrames={T.s2} offset={-OVERLAP}>
        <S2Problem durationInFrames={T.s2} />
      </Series.Sequence>
      <Series.Sequence durationInFrames={T.s3} offset={-OVERLAP}>
        <S3Verdicts durationInFrames={T.s3} />
      </Series.Sequence>
      <Series.Sequence durationInFrames={T.s4} offset={-OVERLAP}>
        <S4Receipts durationInFrames={T.s4} />
      </Series.Sequence>
      <Series.Sequence durationInFrames={T.s5} offset={-OVERLAP}>
        <S5Validator durationInFrames={T.s5} />
      </Series.Sequence>
      <Series.Sequence durationInFrames={T.s6} offset={-OVERLAP}>
        <S6Deserts durationInFrames={T.s6} />
      </Series.Sequence>
      <Series.Sequence durationInFrames={T.s7} offset={-OVERLAP}>
        <S7Override durationInFrames={T.s7} />
      </Series.Sequence>
      <Series.Sequence durationInFrames={T.s8} offset={-OVERLAP}>
        <S8Close durationInFrames={T.s8} />
      </Series.Sequence>
    </Series>
  </>
);

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="FTDDemo"
      component={Video}
      durationInFrames={TOTAL}
      fps={FPS}
      width={1920}
      height={1080}
    />
    <Composition
      id="LiveDemo"
      component={LiveDemo}
      durationInFrames={60 * FPS}
      fps={FPS}
      width={1708}
      height={1000}
    />
  </>
);
