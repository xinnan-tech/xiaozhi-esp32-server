-- 对0.3.0版本之前的参数进行修改
update `sys_params` set param_value = '.mp3;.wav;.p3' where  param_code = 'plugins.play_music.music_ext';