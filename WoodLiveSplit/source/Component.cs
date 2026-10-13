using System;
using System.IO;
using System.Globalization;
using System.Windows.Forms;
using System.Xml;
using LiveSplit.Model;
using LiveSplit.UI;
using LiveSplit.UI.Components;

[assembly: ComponentFactory(typeof(WoodLiveSplit.Factory))]
namespace WoodLiveSplit {
 public sealed class Factory : IComponentFactory {
  public string ComponentName { get { return "Wood TUNG Auto Splitter"; } }
  public string Description { get { return "Receives verified game events from the Wood LiveSplit mod."; } }
  public ComponentCategory Category { get { return ComponentCategory.Control; } }
  public string UpdateName { get { return ComponentName; } }
  public string XMLURL { get { return ""; } }
  public string UpdateURL { get { return ""; } }
  public Version Version { get { return new Version(1,0,0); } }
  public IComponent Create(LiveSplitState state) { return new Component(state); }
 }
 public sealed class Component : LogicComponent {
  public static readonly string[] Route = {"Valves unlocked","Valve 1","Valve 2","Valve 3","Valve 4","Door","Hedge","Finish"};
  readonly LiveSplitState state;
  readonly TimerModel model;
  readonly string directory;
  string attempt="";
  string blockedAttempt="";
  bool owned,disposed;
  DateTime lastRead=DateTime.MinValue;
  string status="Waiting for the Wood LiveSplit mod";
  Label statusLabel;
  public override string ComponentName { get { return "Wood TUNG Auto Splitter"; } }
  public Component(LiveSplitState liveState) : this(liveState,Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Wood","LiveSplit")) { }
  public Component(LiveSplitState liveState,string dataDirectory) {
   state=liveState; model=new TimerModel { CurrentState=state }; directory=dataDirectory;
   state.OnReset+=OnReset;
   InitializeBlankRun();
  }
  void InitializeBlankRun() {
   if(state.CurrentPhase!=TimerPhase.NotRunning || !String.IsNullOrWhiteSpace(state.Run.GameName)
     || !String.IsNullOrWhiteSpace(state.Run.CategoryName) || state.Run.AttemptCount!=0
     || state.Run.AttemptHistory.Count!=0 || state.Run.Count!=1) return;
   var first=state.Run[0];
   if(first.SplitTime.RealTime.HasValue || first.SplitTime.GameTime.HasValue
     || first.PersonalBestSplitTime.RealTime.HasValue || first.PersonalBestSplitTime.GameTime.HasValue
     || first.BestSegmentTime.RealTime.HasValue || first.BestSegmentTime.GameTime.HasValue || first.SegmentHistory.Count!=0) return;
   if(first.Name!="" && first.Name!="Segment" && first.Name!="Split 1" && first.Name!="Start") return;
   state.Run.Clear(); foreach(string name in Route) state.Run.Add(new Segment(name));
   state.Run.GameName="TUNG"; state.Run.CategoryName="Any%"; state.Run.HasChanged=true;
   state.CurrentTimingMethod=TimingMethod.GameTime;
  }
  bool MatchesRun() {
   if(state.Run.GameName!="TUNG" || (state.Run.Count!=8 && state.Run.Count!=1)) return false;
   for(int i=0;i<state.Run.Count;i++)
    if(state.Run[i].Name!=(state.Run.Count==1?"Finish":Route[i])) return false;
   return true;
  }
  void Status(string value) {
   if(status==value)return;
   status=value; if(statusLabel!=null)statusLabel.Text=value;
   try { File.WriteAllText(Path.Combine(directory,"status.txt"),value); } catch { }
  }
  void OnReset(object sender,TimerPhase oldPhase) {owned=false;}
  static bool Number(string text,out double value) {
   return Double.TryParse(text,NumberStyles.Float,CultureInfo.InvariantCulture,out value)
    && !Double.IsNaN(value) && !Double.IsInfinity(value) && value>=-1 && value<=86400;
  }
  public void Step(string snapshot) {
   if(disposed)return;
   string[] s=snapshot.Trim().Split('|'); long stamp; double elapsed;
   if(s.Length!=14 || s[0]!="WOOD-LIVESPLIT/1" || !Int64.TryParse(s[1],out stamp)
    || Math.Abs((DateTime.UtcNow-new DateTime(1970,1,1)).TotalSeconds-stamp)>3
    || !Number(s[4],out elapsed) || elapsed<0) return;
   var events=new double[8];
   for(int i=0;i<8;i++) if(!Number(s[6+i],out events[i]))return;
   if(!MatchesRun()) { owned=false; attempt=s[2]; Status("Open TUNG-AnyPercent.lss, or use one Finish segment"); return; }
   if(s[3]=="disabled") {blockedAttempt=s[2];Status("Automation disabled; start a fresh attempt after enabling");return;}
   if(s[2]==blockedAttempt) {Status("Start a fresh attempt to resume automation");return;}
   bool fresh=attempt!=s[2];
   if(fresh) {
    attempt=s[2];
    if(owned && state.CurrentPhase!=TimerPhase.NotRunning)model.Reset();
    owned=false;
    if(s[3]=="running" && elapsed<=2 && state.CurrentPhase==TimerPhase.NotRunning) {
     state.CurrentTimingMethod=TimingMethod.GameTime; model.Start(); model.InitializeGameTime();
     state.IsGameTimePaused=true; owned=true;
    }
   }
   if(owned && state.CurrentPhase==TimerPhase.NotRunning)owned=false;
   if(!owned) {Status("Connected; start a fresh normal Speedrun attempt");return;}
   if(state.CurrentPhase!=TimerPhase.Running) {Status("Timer paused or ended");return;}
   if(s[3]!="running" && s[3]!="finished") {Status("Holding game time; waiting for a fresh attempt");return;}
   int index=state.CurrentSplitIndex;
   if(state.Run.Count==8) {
    while(index<7 && events[index]>=0) {SetTime(events[index]);model.Split();index++;}
   }
   if(s[3]=="finished" && events[7]>=0) {
    while(state.CurrentSplitIndex<state.Run.Count-1)model.SkipSplit();
    SetTime(events[7]);model.Split();Status("Finished; final time synchronized");
   } else {SetTime(elapsed);Status("Connected; timing normal Any%");}
  }
  void SetTime(double seconds) {state.IsGameTimePaused=true;state.SetGameTime(TimeSpan.FromSeconds(seconds));}
  public override void Update(IInvalidator invalidator,LiveSplitState unused,float width,float height,LayoutMode mode) {
   if(disposed || (DateTime.UtcNow-lastRead).TotalMilliseconds<50)return;
   lastRead=DateTime.UtcNow;
   try {
    string path=Path.Combine(directory,"snapshot.txt");
    if((DateTime.UtcNow-File.GetLastWriteTimeUtc(path)).TotalSeconds>3) {Status("Waiting for fresh game telemetry");return;}
    using(var stream=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))
    using(var reader=new StreamReader(stream))Step(reader.ReadToEnd());
   } catch(IOException) {} catch(UnauthorizedAccessException) {Status("Cannot read game telemetry");}
  }
  public override Control GetSettingsControl(LayoutMode mode) {
   var panel=new FlowLayoutPanel {Dock=DockStyle.Fill,AutoSize=true,FlowDirection=FlowDirection.TopDown};
   panel.Controls.Add(new Label {AutoSize=true,MaximumSize=new System.Drawing.Size(430,0),Text="Install WoodLiveSplit.tungmod in TUNG's Mods folder. Normal Any% only. The supplied eight splits or one Finish segment are supported."});
   statusLabel=new Label {AutoSize=true,MaximumSize=new System.Drawing.Size(430,0),Text=status};panel.Controls.Add(statusLabel);return panel;
  }
  public override XmlNode GetSettings(XmlDocument document) {var node=document.CreateElement("Settings");var version=document.CreateElement("Version");version.InnerText="1.0.0";node.AppendChild(version);return node;}
  public override void SetSettings(XmlNode settings) {}
  public override void Dispose() {if(disposed)return;disposed=true;state.OnReset-=OnReset;if(owned)state.IsGameTimePaused=false;Status("Wood layout closed; automation inactive");}
 }
}
