/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Copyright (c) 2020 IITKGP, INTEL
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as
 * published by the Free Software Foundation;
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 *
 * Author: Argha Sen <arghasen10@gmail.com>
 * Author: Jay Jayatheerthan <jay.jayatheerthan@intel.com>
 * Author: Sandip Chakraborty <sandipchkraborty@gmail.com>
 */
#include "ns3/simulator.h"
#include "ns3/trace-source-accessor.h"
#include "ns3/energy-source.h"
#include "mmwave-radio-energy-model-enb.h"
#include "ns3/log.h"
#include "ns3/config-store-module.h"
#include "ns3/config.h"
#include "ns3/mmwave-enb-phy.h"
#include <fstream>
#include <iomanip>

namespace ns3 {
NS_LOG_COMPONENT_DEFINE ("MmWaveRadioEnergyModelEnb");
NS_OBJECT_ENSURE_REGISTERED (MmWaveRadioEnergyModelEnb);


double Tx_totalduration = 0;//yanyi
TypeId
MmWaveRadioEnergyModelEnb::GetTypeId (void)
{
    static TypeId tid = TypeId ("ns3::MmWaveRadioEnergyModelEnb")
        .SetParent<DeviceEnergyModel> ()
        .AddConstructor<MmWaveRadioEnergyModelEnb> ()
        .AddTraceSource ("TotalEnergyConsumption",
                        "Total energy consumption of the radio device.",
                        MakeTraceSourceAccessor (&MmWaveRadioEnergyModelEnb::m_totalEnergyConsumption),
                        "ns3::TracedValueCallback::Double")
        .AddAttribute ("DeepSleepA",
                        "The default Deep Sleep Current in Amperes.",
                        DoubleValue (0.0001),
                        MakeDoubleAccessor (&MmWaveRadioEnergyModelEnb::SetDeepSleepA,
                                            &MmWaveRadioEnergyModelEnb::GetDeepSleepA),
                        MakeDoubleChecker<double> ())
        .AddAttribute ("RxCurrentA",
                        "The default Rx current in Amperes",
                        DoubleValue (0.0),
                        MakeDoubleAccessor (&MmWaveRadioEnergyModelEnb::SetRxCurrentA,
                                            &MmWaveRadioEnergyModelEnb::GetRxCurrentA),
                        MakeDoubleChecker<double> ())
        .AddAttribute ("TxCurrentA",
                        "The default Tx current in Amperes",
                        DoubleValue(10),
                        MakeDoubleAccessor (&MmWaveRadioEnergyModelEnb::SetTxCurrentA,
                                            &MmWaveRadioEnergyModelEnb::GetTxCurrentA),
                        MakeDoubleChecker<double> ())
        .AddAttribute("Interval", "interval",
                     DoubleValue(0.011),
                     MakeDoubleAccessor(&MmWaveRadioEnergyModelEnb::m_interval),
                     MakeDoubleChecker<double>())
  ;
  return tid;
}
void
MmWaveRadioEnergyModelEnb::SetTotalSize (int totalsize){
  m_totalsize = totalsize;
  // std::cout<<"totalsize: "<<totalsize<<std::endl;
}

MmWaveRadioEnergyModelEnb::MmWaveRadioEnergyModelEnb ()
:
 m_lastUpdateTime (Seconds(0.0))
{
    NS_LOG_FUNCTION (this);
    m_energyDepletionCallback.Nullify ();
    m_source = 0;
    m_currentState = 0;
    m_lastUpdateTime = Seconds (0);
}

MmWaveRadioEnergyModelEnb::~MmWaveRadioEnergyModelEnb ()
{
    NS_LOG_FUNCTION (this);
}

void
MmWaveRadioEnergyModelEnb::SetEnergySource (Ptr<EnergySource> source)
{
    NS_LOG_FUNCTION (this << source);
    NS_ASSERT (source != NULL);
    m_source = source;
}

void
MmWaveRadioEnergyModelEnb::SetNode (Ptr<Node> node)
{
  NS_LOG_FUNCTION (this << node);
  NS_ASSERT (node != NULL);
  m_node = node;
}

Ptr<Node>
MmWaveRadioEnergyModelEnb::GetNode () const
{
  NS_LOG_FUNCTION (this);
  return m_node;
}

double
MmWaveRadioEnergyModelEnb::GetTotalEnergyConsumption (void) const
{
  NS_LOG_FUNCTION (this);
  Time duration = Simulator::Now () - m_lastUpdateTime;
  NS_ASSERT (duration.IsPositive ());
  double energyToDecrease = 0.0;
  double m_Txpower_W = pow(10,(ns3::mmwave::g_txpower-30)/10);//yanyi
  if(m_currentState ==1){
    Time currentTime = Simulator::Now();
    energyToDecrease = duration.GetSeconds()*(m_Txpower_W/0.35+2);//yanyi
    Tx_totalduration +=duration.GetSeconds();
  }
  else if(m_currentState == 2||m_currentState == 3){
    energyToDecrease = duration.GetSeconds()*2*1.01;
  }
  else{
    energyToDecrease = duration.GetSeconds()*2;
  }



  // Time duration = Simulator::Now () - m_lastUpdateTime;
  //   // std::cout<<"111: "<<ns3::mmwave::m_totalSize<<std::endl;
  // NS_ASSERT (duration.IsPositive ());
  // double m_Txpower_W = pow(10,(ns3::mmwave::g_txpower-30)/10);//yanyi
  // double energyToDecrease = 0;
  // double staticpower=12.5;
  // if(m_currentState ==1){
  //   double k=0.021;//拟合后的吞吐量-动态功耗的斜率
  //   energyToDecrease = duration.GetSeconds()*(k+staticpower);
  // }
  // else if(m_currentState == 2||m_currentState == 3){
  //   energyToDecrease = duration.GetSeconds()*staticpower*1.01;
  // }
  // else{
  //   energyToDecrease = duration.GetSeconds()*staticpower;
  // }

  m_source->UpdateEnergySource ();
  
  return m_totalEnergyConsumption + energyToDecrease;
} 

double 
MmWaveRadioEnergyModelEnb::GetDeepSleepA (void) const
{
  NS_LOG_FUNCTION (this);
  return m_deepSleepCurrentA;
}

void
MmWaveRadioEnergyModelEnb::SetDeepSleepA (double deepSleepA)
{
  NS_LOG_FUNCTION (this << deepSleepA);
  m_deepSleepCurrentA = deepSleepA;
}


double 
MmWaveRadioEnergyModelEnb::GetRxCurrentA (void) const
{
  NS_LOG_FUNCTION (this);
  return m_rxCurrentA;
}

void 
MmWaveRadioEnergyModelEnb::SetRxCurrentA (double rxCurrentA)
{
  NS_LOG_FUNCTION (this << rxCurrentA);
  m_rxCurrentA = rxCurrentA;
} 

double 
MmWaveRadioEnergyModelEnb::GetTxCurrentA (void) const
{
  NS_LOG_FUNCTION (this);
  return m_txCurrentA;
}

void 
MmWaveRadioEnergyModelEnb::SetTxCurrentA (double txCurrentA)
{
  NS_LOG_FUNCTION (this << txCurrentA);
  m_txCurrentA = txCurrentA;
}

void
MmWaveRadioEnergyModelEnb::SetEnergyDepletionCallback (
  MmWaveRadioEnergyDepletionCallback callback
)
{
  NS_LOG_FUNCTION (this);
  if (callback.IsNull ())
  {
    NS_LOG_DEBUG ("MmWaveRadioEnergyModelEnb:Setting NULL energy depletion callback!");
  }
  m_energyDepletionCallback = callback;
}

void
MmWaveRadioEnergyModelEnb::SetEnergyRechargedCallback (
  MmWaveRadioEnergyRechargedCallback callback
)
{
  NS_LOG_FUNCTION (this);
  if (callback.IsNull ())
  {
    NS_LOG_DEBUG ("MmWaveRadioEnergyModelEnb:Setting NULL energy recharged callback!");
  }
  m_energyRechargedCallback = callback;
}

void 
MmWaveRadioEnergyModelEnb::ChangeStateEvent(int32_t oldState, int32_t newState)
{
  ChangeState (newState);
}
double totalsize=0;
double throughput=0;
std::ofstream csvFile("throughput_data.csv", std::ios::app);

void 
MmWaveRadioEnergyModelEnb::ChangeState (int state)
{
  NS_LOG_FUNCTION (this << state);

  // std::cout<<"111: "<<ns3::mmwave::m_totalSize<<std::endl;
  int packetsize=ns3::mmwave::m_totalSize;
  // std::cout<<"packetsize="<<packetsize<<std::endl;

  Time duration = Simulator::Now () - m_lastUpdateTime;
  NS_ASSERT (duration.IsPositive ());
  double energyToDecrease = 0.0;
  double m_Txpower_W = pow(10,(ns3::mmwave::g_txpower-30)/10);//yanyi
  if(m_currentState ==1){
    Time currentTime = Simulator::Now();
    energyToDecrease = duration.GetSeconds()*(m_Txpower_W/0.35+2);//yanyi
    Tx_totalduration +=duration.GetSeconds();
  }
  else if(m_currentState == 2||m_currentState == 3){
    energyToDecrease = duration.GetSeconds()*2*1.01;
  }
  else{
    energyToDecrease = duration.GetSeconds()*2;
  }

  // Time duration = Simulator::Now () - m_lastUpdateTime;
  // Time currentTime = Simulator::Now();
  // NS_ASSERT (duration.IsPositive ());
  // double m_Txpower_W = pow(10,(ns3::mmwave::g_txpower-30)/10);//yanyi
  // double energyToDecrease = 0;
  // // double staticpower=12.5;
  // double staticpower=0.01;
  // if(m_currentState ==1){
  //   energyToDecrease = duration.GetSeconds()*(staticpower)+packetsize*8*34.2/734000000;
  //   totalsize += packetsize; 
  //   throughput=totalsize*8/(currentTime.GetSeconds()-0.24)/1024/1024;
  //   csvFile<< currentTime.GetSeconds() <<","<< throughput << "\n";
  // }
  // else if(m_currentState == 2||m_currentState == 3){
  //   energyToDecrease = duration.GetSeconds()*staticpower*1.01;
  // }
  // else{
  //   energyToDecrease = duration.GetSeconds()*staticpower;
  // }
  m_totalEnergyConsumption += energyToDecrease;
  
  m_lastUpdateTime = Simulator::Now ();
  m_source->UpdateEnergySource ();
  m_currentState = state;
  m_previousState = m_currentState;
}

void 
MmWaveRadioEnergyModelEnb::HandleEnergyDepletion (void)
{
  NS_LOG_FUNCTION (this);
  NS_LOG_DEBUG ("MmWaveRadioEnergyModelEnb:Energy is depleted!");
  // invoke energy depletion callback, if set.
  if (!m_energyDepletionCallback.IsNull ())
    {
      m_energyDepletionCallback ();
    }
}

void
MmWaveRadioEnergyModelEnb::HandleEnergyRecharged (void)
{
  NS_LOG_FUNCTION (this);
  NS_LOG_DEBUG ("MmWaveRadioEnergyModelEnb:Energy is recharged!");
  // invoke energy recharged callback, if set.
  if (!m_energyRechargedCallback.IsNull ())
    {
      m_energyRechargedCallback ();
    }
}


/* 
* Private functions start here
*/

void 
MmWaveRadioEnergyModelEnb::DoDispose (void)
{
  NS_LOG_FUNCTION (this);
  m_source = NULL;
  m_energyDepletionCallback.Nullify ();
}

double
MmWaveRadioEnergyModelEnb::GetStateA (int state) const
{
  switch (state)
  {
  case 0:
    return m_deepSleepCurrentA;
  case 1:
    return m_txCurrentA;
  case 2:
    return m_rxCurrentA;
  case 3:
    return m_rxCurrentA;
  }
  NS_FATAL_ERROR ("MmWaveRadioEnergyModelEnb: undefined radio state " << state);
}


void
MmWaveRadioEnergyModelEnb::SetCurrentA (double current)
{
  NS_LOG_FUNCTION (this << current);
    // std::cout<<"111: "<<ns3::mmwave::m_totalSize<<std::endl;
  // Time duration = Simulator::Now () - m_lastUpdateTime;
  // double m_Txpower_W = pow(10,(ns3::mmwave::g_txpower-30)/10);//yanyi
  // double energyToDecrease = 0.0;
  //   if(m_currentState ==1){
  //   Time currentTime = Simulator::Now();
  //   energyToDecrease = duration.GetSeconds()*(m_Txpower_W/0.35+2);//yanyi
  //   Tx_totalduration +=duration.GetSeconds();
  // }
  // else if(m_currentState == 2||m_currentState == 3){
  //   energyToDecrease = duration.GetSeconds()*2*1.01;
  // }
  // else{
  //   energyToDecrease = duration.GetSeconds()*2;
  // }

  Time duration = Simulator::Now () - m_lastUpdateTime;
  // std::cout<<"111: "<<ns3::mmwave::m_totalSize<<std::endl;
  NS_ASSERT (duration.IsPositive ());
  double m_Txpower_W = pow(10,(ns3::mmwave::g_txpower-30)/10);//yanyi
  double energyToDecrease = 0;
  double staticpower=12.5;
  if(m_currentState ==1){
    // energyToDecrease = duration.GetSeconds()*(m_Txpower_W/0.35+2);//yanyi
    // Tx_totalduration +=duration.GetSeconds();
    double throughput= 8000*8/m_interval;
    std::cout<<"interval: "<<m_interval<<std::endl;
 
    double k=0.021;//拟合后的吞吐量-动态功耗的斜率
    energyToDecrease = duration.GetSeconds()*(k*throughput+staticpower);
  }
  else if(m_currentState == 2||m_currentState == 3){
    energyToDecrease = duration.GetSeconds()*staticpower*1.01;
  }
  else{
    energyToDecrease = duration.GetSeconds()*staticpower;
  }

  // update total energy consumption
  m_totalEnergyConsumption += energyToDecrease;
  // update last update time stamp
  m_lastUpdateTime = Simulator::Now ();
  // notify energy source
  m_source->UpdateEnergySource ();
}


double
MmWaveRadioEnergyModelEnb::DoGetCurrentA (void) const
{
  return GetStateA (m_currentState);
}


}
