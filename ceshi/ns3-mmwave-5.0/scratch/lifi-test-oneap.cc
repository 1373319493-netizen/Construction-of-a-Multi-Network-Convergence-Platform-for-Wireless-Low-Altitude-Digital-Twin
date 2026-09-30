
#include "ns3/core-module.h"
#include "ns3/mobility-module.h"
#include "ns3/applications-module.h"
#include "ns3/wifi-module.h"
#include "ns3/network-module.h"
#include "ns3/csma-module.h"
#include "ns3/internet-module.h"
#include <ns3/internet-apps-module.h>
#include "ns3/bridge-helper.h"
#include "ns3/config-store-module.h"
#include <ns3/spectrum-module.h>
#include "ns3/mobility-helper.h"
#include "ns3/packet-sink-helper.h"
#include "ns3/basic-energy-source-helper.h"
#include "ns3/wifi-radio-energy-model-helper.h"
#include "ns3/point-to-point-module.h"
#include "ns3/gnuplot.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/stats-module.h"
#include <ctime>
#include "ns3/yans-wifi-helper.h"
#include <vector>
#include <stdint.h>
#include <sstream>
#include <fstream>
#include "ns3/netanim-module.h"
using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("WiFiDistanceExperiment");


double simTime = 5.0;
void TxCallback (Ptr<CounterCalculator<uint32_t> > datac,
                 std::string path, Ptr<const Packet> packet) {
  NS_LOG_INFO ("Sent frame counted in " <<
               datac->GetKey ());
  // std::cout << "TX packet size: " << packet->GetSize() << std::endl; // yutao
  // datac->Update ();
  Time currentTime = Simulator::Now ();
  datac->Update (packet->GetSize());  
  double throughput=datac->GetCount()*8/(currentTime.GetSeconds()-0.2)/1024/1024;
  // if(currentTime.GetSeconds()>simTime-0.1 && currentTime.GetSeconds()<=simTime){
  // std::cout<<"throughput: "<<throughput<<std::endl;
  // }
  // end TxCallback
}

void RxCallback (Ptr<CounterCalculator<uint32_t> > datac,
                 std::string path, Ptr<const Packet> packet) {
  NS_LOG_INFO ("Sent frame counted in " << datac->GetKey ());
  datac->Update (packet->GetSize());  
  Time currentTime = Simulator::Now ();
  double throughput1=datac->GetCount()*8/(currentTime.GetSeconds()-0.2)/1024/1024;
  std::cout<<"throughput1: "<<throughput1<<std::endl;

  // std::cout<<"PacketSize: "<<packet->GetSize()<<std::endl; 
  // end TxCallback
}

// double m_TotEnergy = 0;

// double CalcTotEnergy(double totEnergy, double currentEnergy){
//   return totEnergy+currentEnergy;
// }


void
AP_1EnergyConsumptionUpdate (double totaloldEnergyConsumption, double totalnewEnergyConsumption)
{
  // m_TotEnergy = CalcTotEnergy(m_TotEnergy, totalnewEnergyConsumption);

  Time currentTime = Simulator::Now ();
 
  // Time currentTime = Simulator::Now ();
  if(currentTime.GetSeconds()>simTime-0.1 && currentTime.GetSeconds()<=simTime){
  // std::cout << "时间:" << currentTime.GetSeconds() << "第一个AP点当前的能耗" << totalnewEnergyConsumption << std::endl;
  std::cout << "时间:" << currentTime.GetSeconds() << "第一个AP点当前的功耗" << (totalnewEnergyConsumption-0.84)/4.8<< std::endl;
  }
  // m_TotEnergy = CalcTotEnergy(m_TotEnergy, totalnewEnergyConsumption);

  std::ofstream energyFile;
  std::string energyFileName = "energyfile-ap1.csv";
  energyFile.open(energyFileName, std::ios_base::out | std::ios_base::app);
  if (energyFile.is_open()) {
    // 写入表头
       if (energyFile.tellp() == 0) {
          energyFile << "Time,NewEnergyConsumption,StateEnergy" << std::endl;
       }
    // 写入数据行
       energyFile << currentTime.GetSeconds() << "," << totalnewEnergyConsumption << "," << totaloldEnergyConsumption << std::endl;
       energyFile.close(); // 关闭文件
  } else {
    std::cerr << "无法打开能源文件1" << std::endl;
  }
} 

static void
SetPosition (Ptr<Node> node, Vector position)
{
  Ptr<MobilityModel> mobility = node->GetObject<MobilityModel> ();
  mobility->SetPosition (position);
}

static void
SetPositionVelocity (Ptr<Node> node, Vector position, Vector velocity)
{
  Ptr<ConstantVelocityMobilityModel> mobility = node->GetObject<ConstantVelocityMobilityModel> ();
  mobility->SetPosition(position);
  mobility->SetVelocity(velocity);
  std::cout<<position.x<<","<<position.y<<std::endl;
}

int main (int argc, char *argv[])
{

  std::string format ("omnet");
  uint32_t nWifis = 1;
  uint32_t nStas = 1;
  bool sendIp = true;
  bool writeMobility = true;
  bool pcap = true;
 
  double simTime_stopInt = 4.0; //2.0;
  double interval =0.058;
  int packetsize = 8000; //200

  CommandLine cmd;
  cmd.AddValue ("nWifis", "Number of wifi networks", nWifis);
  cmd.AddValue ("nStas", "Number of stations per wifi network", nStas);
  cmd.AddValue ("SendIp", "Send Ipv4 or raw packets", sendIp);
  cmd.AddValue ("writeMobility", "Write mobility trace", writeMobility);
  cmd.AddValue ("pcap", "Write pcap traces", pcap);
  cmd.Parse (argc, argv);

  // NODES 
  NodeContainer apNodes; 
  apNodes.Create (nWifis);
  Ptr<Node> serverNode =  CreateObject<Node> ();
  std::vector<NodeContainer> staNodes;

  // DEVICES
  NetDeviceContainer *csmaDevices = new NetDeviceContainer[nWifis + 1]; // APs + serv
  Ipv4InterfaceContainer backboneInterfaces;
  std::vector<NetDeviceContainer> staDevices;
  std::vector<NetDeviceContainer> apDevices;
  std::vector<Ipv4InterfaceContainer> staInterfaces;
  std::vector<Ipv4InterfaceContainer> apInterfaces;
  NetDeviceContainer staDevices1;
  NetDeviceContainer apDevices1;
  
  InternetStackHelper stack;
  // CsmaHelper csma, csma2;
  // csma.SetChannelAttribute("DataRate",StringValue("10000Mbps"));//传输数据速率越大，单位时间接收到的包越多
  // csma.SetChannelAttribute("Delay",TimeValue(NanoSeconds(6560)));
  // csma2.SetChannelAttribute("DataRate",StringValue("10000Mbps"));
  // csma2.SetChannelAttribute("Delay",TimeValue(NanoSeconds(6560)));
  CsmaHelper csma, csma2;
  csma.SetChannelAttribute("DataRate",StringValue("100000Mbps"));//传输数据速率越大，单位时间接收到的包越多
  csma.SetChannelAttribute("Delay",TimeValue(NanoSeconds(10)));
  csma2.SetChannelAttribute("DataRate",StringValue("100000Mbps"));
  csma2.SetChannelAttribute("Delay",TimeValue(NanoSeconds(10)));

  Ipv4AddressHelper ip;
  ip.SetBase ("192.168.0.0", "255.255.255.0");
  stack.Install (apNodes);
  stack.Install(serverNode); 
  // stack.Install(serverNode1);

  // reduce csma queues if needed 
  // Config::SetDefault("ns3::DropTailQueue::MaxPackets", UintegerValue(10));

csmaDevices[0] = csma.Install (NodeContainer(apNodes.Get(0), serverNode));

  Ipv4InterfaceContainer serverInterface;
  serverInterface = ip.Assign(csmaDevices[0].Get(1)); 

  // spectrum channel configuration
  Ptr<MultiModelSpectrumChannel> spectrumChannel= CreateObject<MultiModelSpectrumChannel> ();
  Ptr<LogDistancePropagationLossModel> lossModel = CreateObject<LogDistancePropagationLossModel> ();
	spectrumChannel->AddPropagationLossModel (lossModel);
	Ptr<ConstantSpeedPropagationDelayModel> delayModel= CreateObject<ConstantSpeedPropagationDelayModel> ();
	spectrumChannel->SetPropagationDelayModel (delayModel);

	// spectrum phy configuration
	SpectrumWifiPhyHelper spectrumPhy;
	spectrumPhy.SetChannel (spectrumChannel);
	spectrumPhy.SetErrorRateModel ("ns3::NistErrorRateModel");
	spectrumPhy.Set ("TxPowerStart", DoubleValue (20)); // dBm 
	spectrumPhy.Set ("TxPowerEnd", DoubleValue (20));
  // spectrumPhy.Set("TxGain",DoubleValue (15));
  spectrumPhy.Set("RxGain",DoubleValue (0));
	spectrumPhy.Set ("ChannelWidth", UintegerValue (20));

  
  for (uint32_t ap = 0; ap < nWifis; ++ap){
      std::ostringstream oss;
      oss << "wifi-default";
      Ssid ssid = Ssid (oss.str ());

      NodeContainer sta;
      NetDeviceContainer staDev;
      NetDeviceContainer apDev;
      Ipv4InterfaceContainer staInterface;
      Ipv4InterfaceContainer apInterface;
      MobilityHelper mobility;
      BridgeHelper bridge;
      WifiHelper wifi;
      wifi.SetStandard (WIFI_STANDARD_80211g);
      // wifi.SetStandard (WIFI_PHY_STANDARD_80211n_2_4GHZ);
    
      WifiMacHelper wifiMac;

      sta.Create (nStas);
      mobility.SetPositionAllocator ("ns3::GridPositionAllocator",
                                     "MinX", DoubleValue (0.0),
                                     "MinY", DoubleValue (0.0),
                                     "DeltaX", DoubleValue (5.0),
                                     "DeltaY", DoubleValue (5.0),
                                     "GridWidth", UintegerValue (1),
                                     "LayoutType", StringValue ("RowFirst"));

      // setup the AP.
      mobility.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
      mobility.Install (apNodes.Get (ap));
      wifiMac.SetType ("ns3::ApWifiMac",
                       "Ssid", SsidValue (ssid));
      // Config::SetDefault("ns3::WifiMacQueue::MaxPacketNumber", UintegerValue(20));
      spectrumPhy.Set("ChannelNumber", UintegerValue(1 + (ap % 3) * 5)); 
      apDev = wifi.Install (spectrumPhy, wifiMac, apNodes.Get (ap));

      NetDeviceContainer bridgeDev;
      bridgeDev = bridge.Install (apNodes.Get (ap), 
                                  NetDeviceContainer (apDev, csmaDevices[ap].Get (0)));

      // setup the STAs
      stack.Install (sta);
      /*      mobility.SetMobilityModel ("ns3::RandomWalk2dMobilityModel",
                                 "Mode", StringValue ("Time"),
                                 "Time", StringValue ("2s"),
                                 "Speed", StringValue ("ns3::ConstantRandomVariable[Constant=1.0]"),
                                 "Bounds", RectangleValue (Rectangle (wifiX, wifiX+5.0,0.0, (nStas+1)*5.0))); 
      */
      mobility.SetMobilityModel ("ns3::ConstantVelocityMobilityModel");
      mobility.Install (sta);

      wifiMac.SetType ("ns3::StaWifiMac",
                       "Ssid", SsidValue (ssid),
                       "ActiveProbing", BooleanValue (false));
      staDev = wifi.Install (spectrumPhy, wifiMac, sta);
      staInterface = ip.Assign (staDev);

      // save everything in containers.
      staNodes.push_back (sta);
      apDevices.push_back (apDev);
      apInterfaces.push_back (apInterface);
      staDevices.push_back (staDev);
      staInterfaces.push_back (staInterface);

      SetPosition (apNodes.Get(ap),  Vector (6.25, 6.25, 0.0));
  }
      SetPositionVelocity(staNodes[0].Get(0), Vector(0, 0, 0.0), Vector(0.0, 0.0, 0.0));   


//   sta的位置信息
    // std::string line;  
    // std::ifstream file("/home/great/ns3-mmwave-5.0/src/wifi/examples/sta-2.csv");
    // uint32_t i = 0;  
    // while ( i < nWifis) {  
    //   uint32_t j = 0;  
    //   while ( j < nStas) {  
    //     std::getline(file, line); 
    //     std::istringstream iss(line);  
    //     std::string cell; 
    //     std::getline(iss, cell, ',');
    //     double x = std::stod(cell); 
    //     std::getline(iss, cell, ',');
    //     double y = std::stod(cell);  
    //     SetPositionVelocity(staNodes[i].Get(j), Vector(x, y, 0.0), Vector(0.0, 0.0, 0.0));   
    //     ++j; 
    //   }  
    //   ++i;  
    // }
    // file.close();

for (uint32_t ap = 0; ap < staNodes.size(); ++ap) {
    std::cout << "Number of STA nodes for AP " << ap << ": " << staNodes[ap].GetN() << std::endl;
}

 //double simTime = 5.0;

  for (uint32_t u = 0; u < 1; u++)
    {  
      for (uint32_t sta = 0; sta < nStas; ++sta) {
         ApplicationContainer srv_apps;
         UdpServerHelper srv(9);
        //  std::cout<<"ap id: "<< u <<", user id: "<<staNodes[u].Get(sta)-> GetId() << std::endl;
         
        srv_apps.Add(srv.Install(staNodes[u].Get(sta)));
        srv_apps.Start (Seconds (0.2));
        srv_apps.Stop (Seconds (simTime+simTime_stopInt));  
        
        UdpClientHelper client(staInterfaces[u].GetAddress (sta), 9);
        client.SetAttribute("MaxPackets",UintegerValue (100000000));//232709600
        client.SetAttribute("Interval",TimeValue (Seconds(interval))); 
        client.SetAttribute("PacketSize",UintegerValue (packetsize));//单位是B 8000
        
        ApplicationContainer cln_apps = client.Install (serverNode);
        // cln_apps.Start (Seconds (0.2+sta*0.3));
        // cln_apps.Stop (Seconds (1.8+sta*0.3));
         cln_apps.Start (Seconds (0.2));
         cln_apps.Stop (Seconds (simTime));
      }
    }   
 
//energy
  for (auto dev : apDevices) {
    apDevices1.Add(dev);
}
  
  BasicEnergySourceHelper basicSourceHelper;
  basicSourceHelper.Set ("BasicEnergySourceInitialEnergyJ", DoubleValue (1000000000.0));
  basicSourceHelper.Set ("BasicEnergySupplyVoltageV", DoubleValue (5.0));
  EnergySourceContainer sources = basicSourceHelper.Install (apNodes);
  // EnergySourceContainer switchsource = basicSourceHelper.Install (switchNode);
  
  WifiRadioEnergyModelHelper radioEnergyHelper;
  radioEnergyHelper.Set("Interval", DoubleValue(interval));
  DeviceEnergyModelContainer apEnergyModels = radioEnergyHelper.Install (apDevices1, sources);
  apEnergyModels.Get(0)->TraceConnectWithoutContext ("TotalEnergyConsumption", MakeCallback (&AP_1EnergyConsumptionUpdate));

  // AnimationInterface anim("wifi-anim.xml");

  Ptr<FlowMonitor> flowMonitor;
  FlowMonitorHelper flowHelper;
  flowMonitor = flowHelper.InstallAll();
  uint32_t ReceivedPackets = 0;
  float AvgThroughput = 0;

  DataCollector data;
  data.DescribeRun ( std::to_string(interval),
                    std::to_string(packetsize),"exp", 
                    "yanyi_interval_"+std::to_string(interval)+"_packetsize_"+std::to_string(packetsize));
  
  data.AddMetadata ("author", "Yanyi");


  // Create a counter to track how many frames are generated.  Updates
  // are triggered by the trace signal generated by the WiFi MAC model
  // object.  Here we connect the counter to the signal via the simple
  // TxCallback() glue function defined above.
  Ptr<CounterCalculator<uint32_t> > totalTx_0 =
    CreateObject<CounterCalculator<uint32_t> >();
  totalTx_0->SetKey ("wifi-tx-frames");
  totalTx_0->SetContext ("node[0]");
  Config::Connect ("/NodeList/0/DeviceList/*/$ns3::WifiNetDevice/Mac/MacTx",
                   MakeBoundCallback (&TxCallback, totalTx_0));
  data.AddDataCalculator (totalTx_0);//ap



    Ptr<PacketCounterCalculator> totalRx_2 =
    CreateObject<PacketCounterCalculator>();
  totalRx_2->SetKey ("wifi-rx-mac-traffic");
  totalRx_2->SetContext ("node[2]");
  Config::Connect ("/NodeList/2/DeviceList/*/$ns3::WifiNetDevice/Mac/MacRx",
                   MakeBoundCallback (&RxCallback, totalRx_2));
  data.AddDataCalculator (totalRx_2);

  Simulator::Stop (Seconds(simTime+simTime_stopInt));
  // Simulator::Stop (Seconds(6.0));
  Simulator::Run ();

  //------------------------------------------------------------
  //-- Generate statistics output.
  //--------------------------------------------

  // Pick an output writer based in the requested format.
  Ptr<DataOutputInterface> output = 0;
  if (format == "omnet") {
      NS_LOG_INFO ("Creating omnet formatted data_yutao output.");
      output = CreateObject<OmnetDataOutput>();
    } else if (format == "db") {
    #ifdef STATS_HAS_SQLITE3
      NS_LOG_INFO ("Creating sqlite formatted data_yutao output.");
      output = CreateObject<SqliteDataOutput>();
    #endif
    } else {
      NS_LOG_ERROR ("Unknown output format " << format);
    }

  // Finally, have that writer interrogate the DataCollector and save
  // the results.
  if (output != 0)
    output->Output (data);

  Simulator::Destroy ();
}