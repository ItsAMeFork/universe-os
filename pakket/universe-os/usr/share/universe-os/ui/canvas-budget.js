// Bound fullscreen effects by actual pixel work, independently of CSS geometry.
// Sharp planet textures and text keep their own resolution.
export function canvasScale(width,height,dpr=1,software=false){
 const area=Math.max(1,width)*Math.max(1,height),budget=software?1920*1080:3840*2160;
 return Math.min(Math.max(1,Number(dpr)||1),2,Math.sqrt(budget/area));
}
