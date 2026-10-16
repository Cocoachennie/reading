'use strict';
(function(){
let recovery=null,recoveryExported=false;const el=id=>document.getElementById(id);
function rawExport(){let stored={};try{for(const key of ['leaf-personal',LeafLearning.KEY])stored[key]=localStorage.getItem(key)}catch(e){stored.error=e.message}const payload={format:'leaf-raw-recovery',exported_at:new Date().toISOString(),storage:stored,rollback_originals:recovery};LeafStudy.download(JSON.stringify(payload,null,2),'leaf-original-storage-recovery.json','application/json');recoveryExported=true;el('backup-message').textContent='原始存储已导出。此文件用于排查损坏，不是普通学习备份。请妥善保管。'}
if(legacyStorageError){el('storage-warning').hidden=false;el('storage-warning').textContent='旧版收藏数据无法读取，已暂停写入。请先导出原始存储。'}
try{LeafBackup.legacy(personal)}catch{legacyStorageError=true;el('storage-warning').hidden=false;el('storage-warning').textContent='旧版收藏数据格式异常，已暂停写入。请打开备份与恢复，先导出原始存储。'}
el('export').onclick=()=>{if(LeafReader.locked||legacyStorageError){el('backup-message').textContent='检测到无法读取的旧数据，请先导出原始存储，以免生成不完整备份。';return}LeafReader.saveProgress();try{const payload=LeafBackup.pack(personal,LeafReader.data,el('backup-include-body').checked);LeafStudy.download(JSON.stringify(payload,null,2),'leaf-learning-v2-backup.json','application/json');el('backup-message').textContent='V2 完整学习备份已导出：包含收藏、记录、笔记、词汇和复习记录。是否含正文取决于勾选项。'}catch(e){el('backup-message').textContent='导出失败：'+e.message}};
el('export-raw').onclick=rawExport;
el('backup-file').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;if(file.size>10*1024*1024)throw Error('备份超过 10MB 限制');const incoming=LeafBackup.normalize(JSON.parse(await file.text()));if((LeafReader.locked||legacyStorageError)&&!recoveryExported)throw Error('旧存储损坏，请先点击“导出原始存储”保留原件，再恢复有效备份');
 const nextPersonal=LeafBackup.mergeLegacy(personal,incoming.personal),nextLearning=LeafLearning.merge(LeafReader.data,incoming.learning);
 LeafBackup.commit(localStorage,nextPersonal,nextLearning);personal=nextPersonal;legacyStorageError=false;LeafReader.setData(nextLearning,false);syncOptions();render();LeafStudy.refresh();LeafReader.refreshAnnotations();el('storage-warning').hidden=true;el('backup-message').textContent='恢复成功：已合并现有记录，未清空旧数据。重复备份不会重复计算学习时长或复习日志。';
 }catch(error){if(error.recovery)recovery=error.recovery;el('backup-message').textContent='恢复失败：'+error.message+'。请保留原备份文件。'}finally{e.target.value=''}};
})();
