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

const FPS = 30;

// Scene durations in frames (30 fps).
const T = {
  s1: 150, // 5.0s hook
  s2: 200, // 6.7s data problem
  s3: 240, // 8.0s verdicts
  s4: 210, // 7.0s receipts
  s5: 230, // 7.7s validator
  s6: 230, // 7.7s deserts
  s7: 230, // 7.7s override
  s8: 210, // 7.0s close
};

const TOTAL = Object.values(T).reduce((a, b) => a + b, 0);

const Video: React.FC = () => (
  <Series>
    <Series.Sequence durationInFrames={T.s1}>
      <S1Hook durationInFrames={T.s1} />
    </Series.Sequence>
    <Series.Sequence durationInFrames={T.s2}>
      <S2Problem durationInFrames={T.s2} />
    </Series.Sequence>
    <Series.Sequence durationInFrames={T.s3}>
      <S3Verdicts durationInFrames={T.s3} />
    </Series.Sequence>
    <Series.Sequence durationInFrames={T.s4}>
      <S4Receipts durationInFrames={T.s4} />
    </Series.Sequence>
    <Series.Sequence durationInFrames={T.s5}>
      <S5Validator durationInFrames={T.s5} />
    </Series.Sequence>
    <Series.Sequence durationInFrames={T.s6}>
      <S6Deserts durationInFrames={T.s6} />
    </Series.Sequence>
    <Series.Sequence durationInFrames={T.s7}>
      <S7Override durationInFrames={T.s7} />
    </Series.Sequence>
    <Series.Sequence durationInFrames={T.s8}>
      <S8Close durationInFrames={T.s8} />
    </Series.Sequence>
  </Series>
);

export const RemotionRoot: React.FC = () => (
  <Composition
    id="FTDDemo"
    component={Video}
    durationInFrames={TOTAL}
    fps={FPS}
    width={1920}
    height={1080}
  />
);
