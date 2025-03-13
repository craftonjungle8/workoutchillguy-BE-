[오운완(노션).zip](https://github.com/user-attachments/files/19225506/default.zip)
# 오운완

JIRA: https://kfjgw1t4.atlassian.net/jira/software/projects/BXFD/boards/2

Slack: https://w1710027293-p6w738751.slack.com/archives/C08GP07DK9V

## Overview

1. **개발 동기** 
    
    “올해는 꼭 운동 열심히 한다.” 새해가 되면 빠지지 않고 등장하는 대표적인 결심이다. 그러나 어느덧 2025년의 첫 100일이 지나간 지금, 이 결심을 여전히 실천 중인 사람은 얼마나 될까? 실제로 한 연구에 따르면, 새해 결심을 끝까지 지키는 사람은 5명 중 1명에 불과하다고 한다. 대다수의 사람들은 처음 가졌던 열정과 다짐을 오래 유지하지 못하고 중도에 포기하고 만다.
    
    그렇다면 왜 사람들은 운동이라는 결심을 꾸준히 지키지 못하는 걸까? 여러 이유가 있겠지만, 가장 큰 이유 중 하나는 바로 '기록의 부재'다. 기록이 없다면 자신의 운동 성과나 변화를 명확히 알 수 없고, 결국 동기를 잃게 된다.
    
    이에 우리는 운동을 지속적으로 실천할 수 있는 가장 효과적인 방법으로 ‘기록’을 선택했다. 자신의 운동을 간단히 기록하고 그 기록을 시각적으로 한눈에 확인할 수 있는 운동 관리 서비스를 기획하게 되었다. 이 서비스는 이용자들이 운동 습관을 형성하고, 성취감을 느끼며, 동기를 유지할 수 있도록 돕는다.
    
    이제 누구나 손쉽게 자신의 운동 습관을 체크하고, 꾸준한 운동 습관을 형성할 수 있도록 지원하는 혁신적인 운동관리 서비스를 직접 기획하고 개발하고자 한다.
    
     
    
2.  **주요 서비스 소개**
    1. 일일 운동 기록
        
        메인페이지의 캘린더를 통해 일일 운동일지를 기록 할 수 있다. 운동수행결과 여부에 따라 해당 일자의 배경색이 설정되어 직관적으로 그날의 운동 여부를 확인 할 수 있다운동 기록 차트 & 그래프 제공개인의 출석률과 운동 종류별 수행 빈도를 각각 원그래프와 바차트로 시각화하여 제공함으로써, 사용자가 자신의 운동 습관과 패턴을 한눈에 파악할 수 있도록 돕는다. 이를 통해 사용자는 효과적으로 운동 목표를 설정하고, 자신에게 맞는 운동 방향성을 찾을 수 있다.
        
    2. 운동 메이트 찾기 
        
        어떠한 일을 함에 있어 같은 목표를 가진 동료의 존재는 큰 힘이 된다. 특히 운동과 같이 꾸준함과 의지가 중요한 활동이라면 더욱 그렇다. 오운완은 커뮤니티 내에서 다양한 사람들의 운동 프로필을 제공하여, 자신과 비슷한 운동 스타일과 방향성을 가진 운동메이트를 효과적으로 찾을 수 있도록 지원한다. 함께 운동하며 서로 동기부여하고, 목표를 달성하는 즐거움을 느껴보자.
        
    3. 운동 기록 차트 & 그래프 제공
        
        개인의 출석률과 운동 종류별 수행 빈도를 각각 원그래프와 바차트로 시각화하여 제공함으로써, 사용자가 자신의 운동 습관과 패턴을 한눈에 파악할 수 있도록 돕는다. 이를 통해 사용자는 효과적으로 운동 목표를 설정하고, 자신에게 맞는 운동 방향성을 찾을 수 있다.
        

## 와이어 프레임

[https://embed.figma.com/design/FKJr1MVANQocJirMOf67CC/Untitled?node-id=1-2&t=XP8Fw7Z76CLLis5c-1&embed-host=notion&footer=false&theme=system](https://embed.figma.com/design/FKJr1MVANQocJirMOf67CC/Untitled?node-id=1-2&t=XP8Fw7Z76CLLis5c-1&embed-host=notion&footer=false&theme=system)

## FlowChart

![운동칠가이 플로우차트3.drawio.png]
![Image](https://github.com/user-attachments/assets/f207a4a0-7d35-4d24-af09-4d124a027671)

## Architecture 다이어그램

![Image](https://github.com/user-attachments/assets/03a828c4-b385-42b8-a3de-3a713edd1eaf)

## 기능명세서
<img width="1744" alt="Image" src="https://github.com/user-attachments/assets/39423e46-6e5b-4c1f-807f-8307fb5edade" />

- 추가 희망 및 기능
    - 게시판 대댓글 기능
    - 닉네임 수정 후 업데이트 반영 기능
    - 게시글 작성 제목이 30자 이상 넘어가면 자동으로 알람창 팝업[”글자수를 초과하였습니다.”] 기능
    - 프로필 수정 [출석률과 top 웍스 아웃 차트가 들어가게]
    - 프로필 사진 추가 기능
    - 월별 데이터 제공 ex)캘린더에서 월별 데이터가 자동으로 나오도록
    - 쪽지 기능
    - 운동 종목 추가
    - 게시판 게시글 수정/삭제 시 확인 알람 기능

## ERD

![Image](https://github.com/user-attachments/assets/2b9cdece-c328-4d3e-ba14-22211079f2ef)

[https://www.erdcloud.com/d/iP2go7xxpQrwoHadd](https://www.erdcloud.com/d/iP2go7xxpQrwoHadd)

## 기획 발표 자료

[온라인 운동관리 서비스 오운완.pdf](%E1%84%8B%E1%85%A9%E1%86%AB%E1%84%85%E1%85%A1%E1%84%8B%E1%85%B5%E1%86%AB_%E1%84%8B%E1%85%AE%E1%86%AB%E1%84%83%E1%85%A9%E1%86%BC%E1%84%80%E1%85%AA%E1%86%AB%E1%84%85%E1%85%B5_%E1%84%89%E1%85%A5%E1%84%87%E1%85%B5%E1%84%89%E1%85%B3_%E1%84%8B%E1%85%A9%E1%84%8B%E1%85%AE%E1%86%AB%E1%84%8B%E1%85%AA%E1%86%AB.pdf)

## 최종 발표 자료

[[최종발표자료] 온라인 운동관리 서비스 오운완.pdf](%EC%B5%9C%EC%A2%85%EB%B0%9C%ED%91%9C%EC%9E%90%EB%A3%8C_%EC%98%A8%EB%9D%BC%EC%9D%B8_%EC%9A%B4%EB%8F%99%EA%B4%80%EB%A6%AC_%EC%84%9C%EB%B9%84%EC%8A%A4_%EC%98%A4%EC%9A%B4%EC%99%84.pdf)

# 참고자료

[JWT(JSON Web Token)](https://www.notion.so/JWT-JSON-Web-Token-1b3d5b3e6ec58060988efdc3deef4279?pvs=21)

[Jinja2 SSR(Server-side Rendering)](https://www.notion.so/Jinja2-SSR-Server-side-Rendering-1b3d5b3e6ec580669d3ad125b01faef8?pvs=21)
