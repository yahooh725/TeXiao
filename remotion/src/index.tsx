import React from 'react';
import {AbsoluteFill, Composition, Img, interpolate, registerRoot, useCurrentFrame, useVideoConfig} from 'remotion';

type Track = {frame: number; x: number; y: number; width: number; height: number};
type Overlay = {asset_id: string; asset_data_url: string; tracks_ref: string};
type Props = {
  input_data_url: string;
  fps: number;
  duration_in_frames: number;
  zoom_from: number;
  zoom_to: number;
  tracks: Track[];
  overlays: Overlay[];
  beauty: {preset: string; strength: number};
};

const trackAt = (tracks: Track[], frame: number): Track => {
  if (tracks.length === 0) return {frame, x: 0.25, y: 0.18, width: 0.5, height: 0.58};
  return tracks[Math.min(frame, tracks.length - 1)];
};

const overlayStyle = (id: string, track: Track, scale: number): React.CSSProperties => {
  const centerX = (track.x + track.width / 2) * 100;
  const baseY = (track.y + track.height / 2) * 100;
  const width = id.endsWith('ears') ? track.width * 1.05 : id.endsWith('whiskers') ? track.width * 1.55 : track.width * 0.26;
  const top = id.endsWith('ears') ? (track.y - track.height * 0.24) * 100 : baseY;
  return {
    position: 'absolute',
    left: `${centerX}%`,
    top: `${top}%`,
    width: `${width * 100 * scale}%`,
    transform: 'translate(-50%, -50%)',
    pointerEvents: 'none',
  };
};

const AgentResult: React.FC<Props> = (props) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const track = trackAt(props.tracks, frame);
  const zoom = interpolate(frame, [0, props.duration_in_frames - 1], [props.zoom_from, props.zoom_to], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const beauty = Math.max(0, Math.min(1, props.beauty.strength));
  return (
    <AbsoluteFill style={{backgroundColor: '#dceeff', overflow: 'hidden'}}>
      <AbsoluteFill style={{transform: `scale(${zoom})`, transformOrigin: '50% 50%'}}>
        <Img src={props.input_data_url} style={{width, height, objectFit: 'cover', filter: `brightness(${1 + beauty * 0.06}) saturate(${1 + beauty * 0.08})`}} />
        {props.overlays.map((overlay) => (
          <Img key={overlay.asset_id} src={overlay.asset_data_url} style={overlayStyle(overlay.asset_id, track, overlay.asset_id.endsWith('ears') ? 1 : overlay.asset_id.endsWith('whiskers') ? 1 : 1)} />
        ))}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="AgentResult"
    component={AgentResult}
    width={512}
    height={512}
    fps={30}
    durationInFrames={150}
    defaultProps={{
      input_data_url: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512"><rect width="512" height="512" fill="%23dceeff"/></svg>',
      fps: 30,
      duration_in_frames: 150,
      zoom_from: 1,
      zoom_to: 1.08,
      tracks: [],
      overlays: [],
      beauty: {preset: 'natural_skin', strength: 0.25},
    }}
  />
);

registerRoot(RemotionRoot);
