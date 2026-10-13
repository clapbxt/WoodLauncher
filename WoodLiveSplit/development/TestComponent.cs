using System;
using System.IO;
using System.Threading;
using LiveSplit.Model;
using LiveSplit.Model.Comparisons;
using LiveSplit.Options;
using LiveSplit.UI;
using WoodLiveSplit;
public class TestComponent {
 static void Check(bool condition,string name) {if(!condition)throw new Exception(name);Console.WriteLine("PASS "+name);}
 static LiveSplitState State(string game) {
  var run=new Run(new StandardComparisonGeneratorsFactory()); run.GameName=game;run.CategoryName="";
  run.Add(new Segment("Segment"));
  return new LiveSplitState(run,null,new Layout(),new LayoutSettings(),new Settings());
 }
 static string Frame(int attempt,string phase,double time,string events) {
  long stamp=(long)(DateTime.UtcNow-new DateTime(1970,1,1)).TotalSeconds;
  return "WOOD-LIVESPLIT/1|"+stamp+"|session:"+attempt+"|"+phase+"|"+time.ToString(System.Globalization.CultureInfo.InvariantCulture)+"|0|"+events;
 }
 public static void Main() {
  string empty="-1|-1|-1|-1|-1|-1|-1|-1";
  var state=State("");
  using(var c=new Component(state,Path.GetTempPath())) {
   Check(state.Run.Count==8 && state.Run.GameName=="TUNG","blank run initialized");
   c.Step(Frame(1,"running",0.1,empty));Thread.Sleep(5);
   Check(state.CurrentPhase==TimerPhase.Running,"fresh attempt starts");
   c.Step(Frame(1,"running",10,"2|3|4|5|6|7|8|-1"));
   Check(state.CurrentSplitIndex==7,"seven route splits exactly once");
   Check(state.Run[2].SplitTime.GameTime==TimeSpan.FromSeconds(4),"retained event time");
   c.Step(Frame(1,"running",11,"2|3|4|5|6|7|8|-1"));Check(state.CurrentSplitIndex==7,"no duplicates");
   c.Step(Frame(1,"finished",11.23,"2|3|4|5|6|7|8|11.23"));
   Check(state.CurrentPhase==TimerPhase.Ended && state.Run[7].SplitTime.GameTime==TimeSpan.FromSeconds(11.23),"authoritative finish");
   c.Step(Frame(2,"running",0.1,empty));Thread.Sleep(5);Check(state.CurrentPhase==TimerPhase.Running,"fresh attempt resets owned run");
   new TimerModel {CurrentState=state}.Reset();c.Step(Frame(2,"running",0.2,empty));
   Check(state.CurrentPhase==TimerPhase.NotRunning,"manual reset respected");
   c.Step(Frame(3,"running",40,empty));Check(state.CurrentPhase==TimerPhase.NotRunning,"late attachment rejected");
   c.Step(Frame(4,"running",0.1,empty));Thread.Sleep(5);
   c.Step(Frame(4,"finished",5,"-1|-1|-1|-1|-1|-1|-1|5"));
   Check(state.CurrentPhase==TimerPhase.Ended && !state.Run[0].SplitTime.GameTime.HasValue,"finish skips missing route events");
  }
  var other=State("Other Game");using(var c=new Component(other,Path.GetTempPath())) {
   c.Step(Frame(1,"running",0.1,empty));Check(other.Run.Count==1 && other.Run.GameName=="Other Game" && other.CurrentPhase==TimerPhase.NotRunning,"existing run preserved");
  }
  var saved=State("");saved.Run[0].PersonalBestSplitTime=new Time(null,TimeSpan.FromSeconds(100));
  using(var c=new Component(saved,Path.GetTempPath())) {Check(saved.Run.Count==1 && saved.Run[0].PersonalBestSplitTime.GameTime.HasValue,"unnamed PB preserved");}
  state=State("TUNG");state.Run[0].Name="Finish";
  using(var c=new Component(state,Path.GetTempPath())) {
   c.Step(Frame(1,"running",0.1,empty));Thread.Sleep(5);
   var manual=new TimerModel {CurrentState=state};manual.Pause();
   c.Step(Frame(1,"running",1,empty));Check(state.CurrentPhase==TimerPhase.Paused,"manual pause respected");manual.Pause();
   c.Step(Frame(1,"running",2,"1|1.2|1.4|1.5|1.6|1.7|1.8|-1"));Check(state.CurrentSplitIndex==0,"finish-only ignores intermediate events");
   c.Step(Frame(1,"finished",3,"1|1.2|1.4|1.5|1.6|1.7|1.8|3"));Check(state.CurrentPhase==TimerPhase.Ended,"finish-only ends");
  }
  state=State("TUNG");state.Run[0].Name="Finish";
  using(var c=new Component(state,Path.GetTempPath())) {
   c.Step(Frame(1,"running",0.1,empty));Thread.Sleep(5);
   c.Step(Frame(1,"disabled",1,empty));c.Step(Frame(1,"running",1.5,empty));
   Check(state.CurrentTime.GameTime==TimeSpan.FromSeconds(0.1),"disabled attempt holds timing");
   c.Step(Frame(2,"running",0.1,empty));Check(state.CurrentPhase==TimerPhase.Running && state.CurrentSplitIndex==0,"re-enabled fresh attempt starts");
   c.Step("invalid");Check(state.CurrentPhase==TimerPhase.Running,"partial snapshot ignored");
  }
  Console.WriteLine("Component tests passed");
 }
}
