import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.family']='Liberation Sans'; plt.rcParams['pdf.fonttype']=42
months=['N','D','J','F','M','A','M','J','J','A','S','O']
C=dict(navy='#1F497D',sky='#9DB3CF',amber='#E29628',lamber='#F2C27E',teal='#008080',slate='#8291A0')
rows=[
 ('Kazakh → Kyrgyz power',0,5,C['sky'],'175 GWh'),
 ('Kazakh → Uzbek peak',0,5,C['navy'],'75 GWh'),
 ('Kyrgyz hydro → Uzbek',5,11,C['lamber'],'50 GWh'),
 ('Toktogul water → Uzbek',8,10,C['teal'],'0.18 km³'),
 ('Uzbek → Kazakh repayment',6,11,C['amber'],'337.5 GWh-eq'),
]
fig,ax=plt.subplots(figsize=(4.6,2.6))
for i,(lab,s,e,c,t) in enumerate(rows):
    y=len(rows)-1-i
    ax.barh(y,e-s,left=s,height=0.62,color=c,edgecolor='none')
    tc='white' if c in (C['navy'],C['teal'],C['amber']) else '#222222'
    if e-s<=2: ax.text(s-0.15,y,t,ha='right',va='center',fontsize=11.5,color='#222222')
    else: ax.text((s+e)/2,y,t,ha='center',va='center',fontsize=10.5,color=tc)
ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows][::-1],fontsize=11.5)
ax.set_xticks([x+0.5 for x in range(12)]); ax.set_xticklabels(months,fontsize=11.5)
ax.set_xlim(0,12); ax.set_ylim(-0.6,len(rows)-0.4)
ax.axvspan(0,5,color='#EEF2F8',zorder=0); ax.axvspan(5,12,color='#FDF6EC',zorder=0)
ax.text(2.5,len(rows)-0.45,'Winter',ha='center',va='bottom',fontsize=11.5,color=C['navy'],fontweight='bold')
ax.text(8.5,len(rows)-0.45,'Summer',ha='center',va='bottom',fontsize=11.5,color='#A0661A',fontweight='bold')
for s in ('top','right','left'): ax.spines[s].set_visible(False)
ax.tick_params(axis='y',length=0); ax.tick_params(axis='x',length=2,colors='#444444')
fig.tight_layout(pad=0.3)
fig.savefig('fig7b_barter_calendar.pdf'); fig.savefig('cal.png',dpi=200)
print('ok')
