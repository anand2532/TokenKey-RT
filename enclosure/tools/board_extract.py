#!/usr/bin/env python3
"""Dump TokenKey-RT board facts for enclosure work (KiCad 9 pcbnew Python API).

Usage: python3 board_extract.py <TokenKey-RT.kicad_pcb> [out.json]
Writes the outline, origins, Edge.Cuts segments and every footprint (position, rotation, side,
DNP, courtyard and footprint bounding boxes, 3D model refs, pads) as JSON, and prints a summary.
Coordinates are KiCad page mm (y down); pos_from_aux_ll_mm assumes the aux origin is (0, 40).
"""
import pcbnew, json, sys
PCB = sys.argv[1] if len(sys.argv) > 1 else 'hardware/schematic/TokenKey-RT.kicad_pcb'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'board_extract_raw.json'
B = pcbnew.LoadBoard(PCB)
mm = pcbnew.ToMM
out = {"source":{"file":PCB}}
bb = B.GetBoardEdgesBoundingBox()
out["board"]={"bbox_mm":[mm(bb.GetLeft()),mm(bb.GetTop()),mm(bb.GetRight()),mm(bb.GetBottom())],
 "size_mm":[mm(bb.GetWidth()),mm(bb.GetHeight())],
 "thickness_mm":mm(B.GetDesignSettings().GetBoardThickness()),
 "aux_origin_mm":[mm(B.GetDesignSettings().GetAuxOrigin().x),mm(B.GetDesignSettings().GetAuxOrigin().y)],
 "grid_origin_mm":[mm(B.GetDesignSettings().GetGridOrigin().x),mm(B.GetDesignSettings().GetGridOrigin().y)],
 "edge_cuts":[]}
for d in B.GetDrawings():
    if d.GetLayer()==pcbnew.Edge_Cuts:
        e={"shape":d.ShowShape(),"start":[mm(d.GetStart().x),mm(d.GetStart().y)],"end":[mm(d.GetEnd().x),mm(d.GetEnd().y)]}
        if d.GetShape()==pcbnew.SHAPE_T_ARC: e["radius"]=round(mm(d.GetRadius()),3)
        out["board"]["edge_cuts"].append(e)
fps=[]
for f in B.GetFootprints():
    pos=f.GetPosition()
    f.BuildCourtyardCaches()
    cy=f.GetCourtyard(pcbnew.F_CrtYd if f.GetLayer()==pcbnew.F_Cu else pcbnew.B_CrtYd)
    cbb=cy.BBox() if cy.OutlineCount() else None
    fb=f.GetBoundingBox(False)
    pads=[]
    for p in f.Pads():
        pads.append({"num":p.GetNumber(),"pos":[round(mm(p.GetPosition().x),3),round(mm(p.GetPosition().y),3)],
          "size":[round(mm(p.GetSize(pcbnew.F_Cu).x),3),round(mm(p.GetSize(pcbnew.F_Cu).y),3)] if hasattr(p,'GetSize') else None,
          "drill":[round(mm(p.GetDrillSize().x),3),round(mm(p.GetDrillSize().y),3)],"attr":p.GetAttribute(),"net":p.GetNetname()})
    fps.append({"ref":f.GetReference(),"value":f.GetValue(),"footprint":str(f.GetFPID().GetUniStringLibId()),
     "pos_mm":[round(mm(pos.x),3),round(mm(pos.y),3)],"pos_from_aux_ll_mm":[round(mm(pos.x),3),round(40-mm(pos.y),3)],
     "rot_deg":f.GetOrientationDegrees(),"side":"bottom" if f.IsFlipped() else "top",
     "dnp":f.IsDNP(),
     "courtyard_bbox":[round(mm(cbb.GetLeft()),3),round(mm(cbb.GetTop()),3),round(mm(cbb.GetRight()),3),round(mm(cbb.GetBottom()),3)] if cbb else None,
     "fp_bbox":[round(mm(fb.GetLeft()),3),round(mm(fb.GetTop()),3),round(mm(fb.GetRight()),3),round(mm(fb.GetBottom()),3)],
     "models":[{"file":m.m_Filename,"offset":[m.m_Offset.x,m.m_Offset.y,m.m_Offset.z],"rot":[m.m_Rotation.x,m.m_Rotation.y,m.m_Rotation.z],"scale":[m.m_Scale.x,m.m_Scale.y,m.m_Scale.z],"show":m.m_Show} for m in f.Models()],
     "fields":{fl.GetName():fl.GetText() for fl in f.GetFields() if fl.GetName() not in ("Reference","Value","Footprint")},
     "pads":pads})
out["footprints_all"]=fps
json.dump(out,open(OUT,'w'),indent=1)
for f in sorted(fps,key=lambda x:x['ref']):
    print(f"{f['ref']:5} {f['side'][0]} {f['pos_mm']} r{f['rot_deg']:.0f} {f['footprint']} cy={f['courtyard_bbox']} models={[m['file'].split('/')[-1] for m in f['models']]} {'DNP' if f['dnp'] else ''}")
print(json.dumps(out["board"],indent=0))
