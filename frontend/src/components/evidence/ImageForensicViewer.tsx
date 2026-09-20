import React, { useState } from 'react';
import { Eye, ZoomIn, Info, CheckCircle, AlertTriangle } from 'lucide-react';
import { VisualEvidencePanel } from '../../types';

interface Props {
  panels: VisualEvidencePanel[];
}

export const ImageForensicViewer: React.FC<Props> = ({ panels }) => {
  const [selectedId, setSelectedId] = useState<string>(panels[0]?.id || 'dup_flooding');

  const currentPanel = panels.find(p => p.id === selectedId) || panels[0];

  if (!panels || panels.length === 0) {
    return (
      <div className="bg-[#0b101d] border border-slate-800 p-8 rounded-xl text-center text-slate-400">
        No visual evidence panels generated. Run `python scripts/generate_visual_evidence.py` to produce visual artifacts.
      </div>
    );
  }

  return (
    <div className="bg-[#0b101d] border border-slate-800 rounded-xl overflow-hidden">
      {/* Panel Navigation Tabs */}
      <div className="flex border-b border-slate-800 bg-slate-900/60 overflow-x-auto p-1.5 gap-1">
        {panels.map(p => {
          const isSelected = p.id === selectedId;
          return (
            <button
              key={p.id}
              onClick={() => setSelectedId(p.id)}
              className={`px-3 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition-all flex items-center gap-2 ${
                isSelected
                  ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40 border border-transparent'
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              <span>{p.title}</span>
            </button>
          );
        })}
      </div>

      {/* Main Forensic Inspection Area */}
      {currentPanel && (
        <div className="p-5 space-y-4">
          <div className="flex flex-col md:flex-row justify-between md:items-center gap-3">
            <div>
              <h3 className="text-base font-semibold text-white tracking-wide">
                {currentPanel.title}
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                {currentPanel.description}
              </p>
            </div>

            {/* Metrics Pills */}
            <div className="flex items-center gap-2 flex-wrap">
              {Object.entries(currentPanel.metrics || {}).map(([key, val]) => (
                <div
                  key={key}
                  className="bg-slate-900/90 border border-slate-800 px-2.5 py-1 rounded text-xs font-mono"
                >
                  <span className="text-slate-400 capitalize mr-1.5">{key.replace(/_/g, ' ')}:</span>
                  <span className="text-cyan-300 font-semibold">{String(val)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Evidence Image Container */}
          <div className="relative bg-black rounded-lg border border-slate-800/90 overflow-hidden flex items-center justify-center min-h-[320px] max-h-[500px]">
            <img
              src={currentPanel.image_url}
              alt={currentPanel.title}
              className="max-h-[480px] w-auto object-contain rounded select-none"
              onError={(e) => {
                // Fallback placeholder if image not yet generated
                (e.target as HTMLElement).style.display = 'none';
              }}
            />
            {/* Overlay watermark */}
            <div className="absolute bottom-2 right-3 font-mono text-[10px] text-slate-500 bg-black/60 px-2 py-0.5 rounded pointer-events-none">
              OFFLINE FORENSIC VISUAL EVIDENCE • SHA-256 VERIFIED
            </div>
          </div>

          {/* Technical Explanations */}
          <div className="bg-slate-900/40 border border-slate-800/80 p-3.5 rounded-lg flex items-start gap-2.5 text-xs text-slate-300">
            <Info className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="font-semibold text-white font-mono uppercase text-[11px] block">
                Forensic Analysis Method
              </span>
              <p className="text-slate-300 leading-relaxed text-xs">
                {currentPanel.id === 'dup_flooding' &&
                  '3-tier validation: Initial SHA-256 byte comparison, candidate filtering via perceptual pHash/dHash hamming distance <= 6, confirmed by SSIM >= 0.82 and normalized pixel MAE <= 0.15.'}
                {currentPanel.id === 'label_manipulation' &&
                  'Object ROI feature extraction with k-NN neighborhood consensus (k=5) measuring centroid distance margin discrepancies between assigned and predicted semantic categories.'}
                {currentPanel.id === 'ood_insertion' &&
                  'Isolation Forest density modeling over multi-scale color moments, texture GLCM energy, and Laplacian edge sharpness identifying departures from baseline aerial domain distributions.'}
                {currentPanel.id === 'corner_trigger' &&
                  'Border-zone sliding window variance analysis and Laplacian edge density filtering detecting localized high-contrast checkerboard BadNets triggers.'}
                {currentPanel.id === 'blended_watermark' &&
                  'Spatial high-pass residual autocorrelation detecting uniform low-opacity alpha watermark patterns blended across target image planes.'}
                {currentPanel.id === 'spectral_fft' &&
                  '2D Fast Fourier Transform (FFT) frequency spectrum extraction highlighting periodic sinusoidal carrier spikes exceeding z-score threshold >= 6.12.'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
