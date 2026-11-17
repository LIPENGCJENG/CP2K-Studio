"""Reproducible offscreen UI captures, including narrow/wide and HiDPI layouts.

Run with .venv/bin/python scripts/capture_ui.py [--scale 2].
This renders the explicit bundled water example; no CP2K process is launched.
"""
import argparse
import os
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--scale',type=int,choices=[1,2],default=1)
    parser.add_argument('--output',type=Path,default=ROOT/'docs/images/ui-ux')
    args=parser.parse_args()
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    os.environ['QT_SCALE_FACTOR']=str(args.scale)
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage,QPainter,QColor,QFont
    from PySide6.QtWidgets import QApplication
    from core.project_io import load_project
    from ui.main_window import MainWindow
    app=QApplication([])
    project=load_project(ROOT/'examples/water.cp2kstudio.json')
    with tempfile.TemporaryDirectory(prefix='studio-ui-capture-') as folder:
        window=MainWindow(preset_directory=folder)
        window.show()
        def settle():
            for _ in range(6):app.processEvents()
        def save(path):
            settle()
            pixmap=window.grab()
            assert not pixmap.isNull()
            assert pixmap.save(str(path))
            return pixmap.devicePixelRatio()
        sizes=[(1366,768),(1920,1080)] if args.scale==1 else [(1366,768)]
        for width,height in sizes:
            output=args.output/(f'{width}x{height}' if args.scale==1 else 'retina-2x')
            output.mkdir(parents=True,exist_ok=True)
            window.resize(width,height)
            pages=[]
            indices=range(8) if args.scale==1 else [0,2,4,6]
            for index in indices:
                p=project.model_copy(deep=True)
                if index==5:p.global_settings.run_type='GEO_OPT'
                window.load_into_ui(p)
                window.nav.setCurrentRow(index)
                window.stack.widget(index).verticalScrollBar().setValue(0)
                path=output/f'{index+1:02}.png'
                dpr=save(path)
                assert window.stack.widget(index).horizontalScrollBar().maximum()==0
                pages.append(path)
                print(f'{path.relative_to(ROOT) if path.is_relative_to(ROOT) else path} · DPR {dpr}')
                if index==0:
                    # The 3D view is persistent in the right pane on every page.
                    window.stack.widget(index).ensureWidgetVisible(window.structure_panel.coords,0,8)
                    save(output/'01-view.png')
                if index==4:
                    window.stack.widget(index).ensureWidgetVisible(window.kind_panel.table,0,8)
                    save(output/'05-table.png')
            if args.scale==1:
                p=project.model_copy(deep=True)
                p.dft.scf.method='DIAGONALIZATION'
                window.load_into_ui(p);window.nav.setCurrentRow(3)
                save(output/'04-diagonalization.png')
                # Overview is for navigation; individual captures retain full resolution.
                tw,th=683,384
                sheet=QImage(tw*2,(th+28)*4,QImage.Format.Format_RGB32)
                sheet.fill(QColor('#172333'))
                painter=QPainter(sheet);painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                painter.setFont(QFont(app.font().family(),11))
                painter.setPen(QColor('#b8d8e5'))
                for i,path in enumerate(pages):
                    x,y=(i%2)*tw,(i//2)*(th+28)
                    painter.drawText(x+12,y+20,f'{i+1:02}  '+['结构与晶胞','GLOBAL','DFT','SCF','基组与赝势','几何优化','运行环境','导出与预设'][i])
                    painter.drawImage(x,y+28,QImage(str(path)).scaled(tw,th,Qt.AspectRatioMode.IgnoreAspectRatio,Qt.TransformationMode.SmoothTransformation))
                painter.end();sheet.save(str(output/'overview.png'))
        window.dirty=False;window.close()


if __name__=='__main__':main()
