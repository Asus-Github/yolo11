from PIL import Image
import os
for f in ['figures/fig7_main_metrics.png','figures/fig8_class_map_gain.png','figures/fig9_training_map50_95.png','figures/fig10_training_recall.png','figures/fig_detection_comparison.png','figures/fig_detection_comparison_full.png']:
    try:
        im=Image.open(f); print(f, im.size)
    except Exception as e:
        print(f, 'ERR', e)
print('--- media ---')
for f in sorted(os.listdir('_tmp_cur/word/media')):
    im = Image.open('_tmp_cur/word/media/'+f)
    print(f, im.size)
