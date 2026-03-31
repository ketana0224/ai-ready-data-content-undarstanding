# クラウド一覧

代表的なクラウドを以下一覧します。


<table>
<tr>
<td>クラウド</td>
<td>特徴</td>
</tr>
<tr>
<td>Azure</td>
<td>PaaS</td>
</tr>
<tr>
<td>AWS</td>
<td>IaaS</td>
</tr>
</table>


![Start App is accessed via HTTP(S) from Internet? Yes IDPS required? Yes AppGW/WAF in front of AzFW No No AzFW only AppGW/WAF and AzFW in parallel](figures/1.1)

> Figure 1.1 description: この図版は、アプリ公開時に **Azure Firewall（AzFW）** と **Application Gateway / WAF（AppGW/WAF）** をどう配置するかを判断するためのフローチャートです。上部の **Start** から始まり、最初に「**App is accessed via HTTP(S) from Internet?**（アプリはインターネットから HTTP(S) でアクセスされるか）」を判定します。ここで **No** の場合は下方向に進み、構成は **AzFW only**（Azure Firewall のみ）となります。  
一方で **Yes** の場合は次の判断「**IDPS required?**（侵入検知・防御機能が必要か）」に進み、**Yes** なら **AppGW/WAF in front of AzFW**（Application Gateway / WAF を Azure Firewall の前段に配置）、**No** なら **AppGW/WAF and AzFW in parallel**（両者を並列配置）という結論になります。図中に数値・軸・凡例はなく、主メッセージは「インターネット公開の有無と IDPS 要件に応じて、AzFW と AppGW/WAF の適切な配置パターンを選ぶ」という点です。

このプロセスは、公開アプリの通信方式とセキュリティ要件を基に、ネットワークセキュリティ製品の配置方法を決定する流れです。まずアプリがインターネットから HTTP(S) 経由で利用されるかを確認し、そうでなければ Azure Firewall のみを使います。HTTP(S) 公開される場合は、次に IDPS が必要かを判定し、必要なら WAF を Azure Firewall の前段に置き、不要なら WAF と Azure Firewall を並列に配置します。

```mermaid
flowchart TD
    A([Start]) --> B{App is accessed via HTTP(S) from Internet?}
    B -- No --> C([AzFW only])
    B -- Yes --> D{IDPS required?}
    D -- Yes --> E([AppGW/WAF in front of AzFW])
    D -- No --> F([AppGW/WAF and AzFW in parallel])
```

