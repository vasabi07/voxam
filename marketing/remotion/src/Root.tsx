import "./index.css";
import { Composition } from "remotion";
import { MyComposition } from "./Composition";
import {
  InstagramAd,
  INSTAGRAM_AD_DURATION,
  INSTAGRAM_AD_FPS,
  INSTAGRAM_AD_WIDTH,
  INSTAGRAM_AD_HEIGHT,
} from "./InstagramAd";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* Original demo composition */}
      <Composition
        id="MyComp"
        component={MyComposition}
        durationInFrames={60}
        fps={30}
        width={1280}
        height={720}
      />

      {/* Instagram Ad - 9:16 vertical format for Reels */}
      <Composition
        id="InstagramAd"
        component={InstagramAd}
        durationInFrames={INSTAGRAM_AD_DURATION}
        fps={INSTAGRAM_AD_FPS}
        width={INSTAGRAM_AD_WIDTH}
        height={INSTAGRAM_AD_HEIGHT}
      />
    </>
  );
};
