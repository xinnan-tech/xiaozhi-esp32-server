 Commands to start the servers:

  Backend (Spring Boot):
  cd main/manager-api
  mvn spring-boot:run

  Frontend (Vue.js):
  cd main/manager-web
  npm run serve

  The backend runs on port 8002 at http://localhost:8002/xiaozhi
  The frontend runs on port 8001 at http://localhost:8001/


The backend requires Java 21. 
Update(main/manager-api/pom.xml)
  ⎿  Updated main/manager-api/pom.xml with 1 addition and 1 removal                            
       17        <properties>
       18            <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
       19            <project.reporting.outputEncoding>UTF-8</project.reporting.outputEncoding>
       20 -          <java.version>21</java.version>
       20 +          <java.version>17</java.version>


The getFirst() method is a Java 21 feature.
fix both files to use Java 17 compatible code:

⏺ Update(main/manager-api/src/main/java/xiaozhi/modules/device/service/impl/OtaServiceImpl.java)
  ⎿  Updated main/manager-api/src/main/java/xiaozhi/modules/device/service/impl/OtaServiceImpl.java with 1 addition and 1 removal
       66            // 同类固件只保留最新的一条
       67            List<OtaEntity> otaList = baseDao.selectList(queryWrapper);
       68            if (otaList != null && otaList.size() > 0) {
       69 -              OtaEntity otaBefore = otaList.getFirst();
       69 +              OtaEntity otaBefore = otaList.get(0);



There's a syntax error in the Liquibase configuration file. Let me check and fix it:

⏺ Read(main/manager-api/src/main/resources/db/changelog/db.changelog-master.yaml)
  ⎿  Read 249 lines (ctrl+r to expand)

⏺ I see the issue - there's a duplicate id field at line 243. Let me fix this:

⏺ Update(main/manager-api/src/main/resources/db/changelog/db.changelog-master.yaml)
  ⎿  Updated main/manager-api/src/main/resources/db/changelog/db.changelog-master.yaml with 2 additions and 1 removal
       240            - sqlFile:
       241                encoding: utf8
       242                path: classpath:db/changelog/202506261637.sql
       243 -        id: 202506152342
       243 +    - changeSet:
       244 +        id: 202507051233
       245          author: marlonz
       246          changes:
       247            - sqlFile:

       restart the backend