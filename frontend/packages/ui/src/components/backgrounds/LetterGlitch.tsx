import { useRef, useEffect } from 'react';
import { BackgroundLayer, useTokens, useVisibility } from './BackgroundLayer';

interface RGB { r: number; g: number; b: number }
interface Letter { char: string; rgb: RGB; fromRgb: RGB; targetRgb: RGB; colorProgress: number }

const FALLBACK_RGB: RGB = { r: 255, g: 255, b: 255 };

export interface LetterGlitchProps {
  /* 字符色；默认取 Design Token --color-blue-team */
  glitchColors?: string[];
  className?: string;
  /* 故障刷新间隔 ms；越大越慢，8.7.1 取最低档 */
  glitchSpeed?: number;
  centerVignette?: boolean;
  outerVignette?: boolean;
  smooth?: boolean;
  lightMode?: boolean;
  backgroundColor?: string;
  /* ASCII + 十六进制字符集（呼应密钥/哈希意象，8.7.1） */
  characters?: string;
  /* 整体不透明度，默认 0.2（8.7.1：--color-blue-team 20% 不透明度） */
  opacity?: number;
}

export function LetterGlitch({
  glitchColors,
  className = '',
  glitchSpeed = 120,
  centerVignette = false,
  outerVignette = true,
  smooth = true,
  lightMode = false,
  backgroundColor,
  characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$&*()-_+=/[]{};:<>.,0123456789',
  opacity = 0.2
}: LetterGlitchProps) {
  const tokens = useTokens();
  const visible = useVisibility();
  const visibleRef = useRef(visible);
  visibleRef.current = visible;
  const colors = glitchColors ?? [tokens.blue, tokens.blue, tokens.blue];

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animationRef = useRef(0);
  const letters = useRef<Letter[]>([]);
  const grid = useRef({ columns: 0, rows: 0 });
  const context = useRef<CanvasRenderingContext2D | null>(null);
  const lastGlitchTime = useRef(Date.now());

  const lettersAndSymbols = Array.from(characters);

  const fontSize = 16;
  const charWidth = 10;
  const charHeight = 20;

  const getRandomChar = () => {
    return lettersAndSymbols[Math.floor(Math.random() * lettersAndSymbols.length)];
  };

  const getRandomColor = () => {
    return colors[Math.floor(Math.random() * colors.length)];
  };

  const hexToRgb = (hex: string): RGB | null => {
    const shorthandRegex = /^#?([a-f\d])([a-f\d])([a-f\d])$/i;
    const expanded = hex.replace(shorthandRegex, (_m, r, g, b) => r + r + g + g + b + b);
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(expanded);
    return result
      ? { r: parseInt(result[1], 16), g: parseInt(result[2], 16), b: parseInt(result[3], 16) }
      : null;
  };

  const mixRgb = (start: RGB, end: RGB, factor: number): RGB => ({
    r: Math.round(start.r + (end.r - start.r) * factor),
    g: Math.round(start.g + (end.g - start.g) * factor),
    b: Math.round(start.b + (end.b - start.b) * factor)
  });

  const rgbToCss = ({ r, g, b }: RGB) => `rgb(${r}, ${g}, ${b})`;

  const getRandomRgb = () => hexToRgb(getRandomColor()) ?? FALLBACK_RGB;

  const calculateGrid = (width: number, height: number) => {
    const columns = Math.ceil(width / charWidth);
    const rows = Math.ceil(height / charHeight);
    return { columns, rows };
  };

  const initializeLetters = (columns: number, rows: number) => {
    grid.current = { columns, rows };
    const totalLetters = columns * rows;
    letters.current = Array.from({ length: totalLetters }, () => {
      const rgb = getRandomRgb();
      return { char: getRandomChar(), rgb, fromRgb: rgb, targetRgb: getRandomRgb(), colorProgress: 1 };
    });
  };

  const resizeCanvas = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const parent = canvas.parentElement;
    if (!parent) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = parent.getBoundingClientRect();

    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;

    canvas.style.width = `${rect.width}px`;
    canvas.style.height = `${rect.height}px`;

    if (context.current) {
      context.current.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    const { columns, rows } = calculateGrid(rect.width, rect.height);
    initializeLetters(columns, rows);

    drawLetters();
  };

  const drawLetters = () => {
    const canvasEl = canvasRef.current;
    if (!context.current || letters.current.length === 0 || !canvasEl) return;
    const ctx = context.current;
    const { width, height } = canvasEl.getBoundingClientRect();
    ctx.clearRect(0, 0, width, height);
    ctx.font = `${fontSize}px monospace`;
    ctx.textBaseline = 'top';

    letters.current.forEach((letter, index) => {
      const x = (index % grid.current.columns) * charWidth;
      const y = Math.floor(index / grid.current.columns) * charHeight;
      ctx.fillStyle = rgbToCss(letter.rgb);
      ctx.fillText(letter.char, x, y);
    });
  };

  const updateLetters = () => {
    if (!letters.current || letters.current.length === 0) return;

    const updateCount = Math.max(1, Math.floor(letters.current.length * 0.05));

    for (let i = 0; i < updateCount; i++) {
      const index = Math.floor(Math.random() * letters.current.length);
      if (!letters.current[index]) continue;

      letters.current[index].char = getRandomChar();
      letters.current[index].fromRgb = letters.current[index].rgb;
      letters.current[index].targetRgb = getRandomRgb();

      if (!smooth) {
        letters.current[index].rgb = letters.current[index].targetRgb;
        letters.current[index].colorProgress = 1;
      } else {
        letters.current[index].colorProgress = 0;
      }
    }
  };

  const handleSmoothTransitions = () => {
    let needsRedraw = false;
    letters.current.forEach((letter) => {
      if (letter.colorProgress < 1) {
        letter.colorProgress += 0.05;
        if (letter.colorProgress > 1) letter.colorProgress = 1;

        letter.rgb = mixRgb(letter.fromRgb, letter.targetRgb, letter.colorProgress);
        needsRedraw = true;
      }
    });

    if (needsRedraw) {
      drawLetters();
    }
  };

  const animate = () => {
    animationRef.current = requestAnimationFrame(animate);
    if (!visibleRef.current || document.hidden) return;

    const now = Date.now();
    if (now - lastGlitchTime.current >= glitchSpeed) {
      updateLetters();
      drawLetters();
      lastGlitchTime.current = now;
    }

    if (smooth) {
      handleSmoothTransitions();
    }
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    context.current = canvas.getContext('2d');
    resizeCanvas();
    animate();

    let resizeTimeout: number | undefined;

    const handleResize = () => {
      if (resizeTimeout) clearTimeout(resizeTimeout);
      resizeTimeout = window.setTimeout(() => {
        cancelAnimationFrame(animationRef.current);
        resizeCanvas();
        animate();
      }, 100);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animationRef.current);
      window.removeEventListener('resize', handleResize);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [glitchSpeed, smooth]);

  const containerStyle: React.CSSProperties = {
    position: 'relative',
    width: '100%',
    height: '100%',
    backgroundColor: backgroundColor ?? (lightMode ? '#ffffff' : tokens.base),
    overflow: 'hidden'
  };

  const canvasStyle: React.CSSProperties = {
    display: 'block',
    width: '100%',
    height: '100%'
  };

  const outerVignetteStyle: React.CSSProperties = {
    position: 'absolute',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    pointerEvents: 'none',
    background: lightMode
      ? 'radial-gradient(circle, rgba(255,255,255,0) 58%, rgba(255,255,255,0.96) 100%)'
      : 'radial-gradient(circle, rgba(0,0,0,0) 60%, rgba(0,0,0,1) 100%)'
  };

  const centerVignetteStyle: React.CSSProperties = {
    position: 'absolute',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    pointerEvents: 'none',
    background: lightMode
      ? 'radial-gradient(circle, rgba(255,255,255,0.9) 0%, rgba(255,255,255,0) 60%)'
      : 'radial-gradient(circle, rgba(0,0,0,0.8) 0%, rgba(0,0,0,0) 60%)'
  };

  return (
    <BackgroundLayer className={className}>
      <div style={{ ...containerStyle, opacity }}>
        <canvas ref={canvasRef} style={canvasStyle} />
        {outerVignette && <div style={outerVignetteStyle}></div>}
        {centerVignette && <div style={centerVignetteStyle}></div>}
      </div>
    </BackgroundLayer>
  );
}
