"""

"""
import json
def  test():
    from idl_parser import parser
    _parser = parser.IDLParser()
    idl_str = '''
#ifndef _JAUS_GLOBALLOITERDRIVER_INCLUDED_
#define _JAUS_GLOBALLOITERDRIVER_INCLUDED_

module ext {
	@annotation jaus_extends {
		string value;
	};
	@annotation jaus_presence_vector_field {
	};
	@annotation jaus_recommended_query{
		string value;
	};
};
struct Empty {};

struct JausAddress
{
    uint16 subsystem;
    uint8 node;
    uint8 component;
};

const JausAddress ANY_JAUS_ADDRESS = {0xff, 0xf, 0xf};

typedef uint16 JausMessageId;

const JausMessageId ANY_JAUS_MESSAGE = 0xff;

struct JausService {
    //! Service URI
    string<255> uRI;
    //! Major version number of the service
    @unit("one") uint8 majorVersionNumber;
    //! Minor version number of the service
    @unit("one") uint8 minorVersionNumber;
};

typedef map<JausAddress, sequence<JausService>> JausServiceMap;

struct HeaderRec
{
    short id;
    sequence<short, 255> spoolIDRec_;
};


@ext::jaus_extends("events")
module VelocityStateSensor {
    struct QueryVelocityStateData {

        //! See Report Velocity State Message
        @ext::jaus_presence_vector_field @unit("one") uint16 presenceVector;
    };

    struct QueryVelocityStateExtData {
      struct QueryVelocityStateExtRec {

          //! Requested presence vector associated with the velocity variant
          @ext::jaus_presence_vector_field @unit("one") uint8 velocityVarPresenceVector;

          //! Requested presence vector associated with the ReportVelocityStateExtRec
          @ext::jaus_presence_vector_field @unit("one") uint16 reportVelocityStateExtRecPresenceVector;
      };

      QueryVelocityStateExtRec queryVelocityStateExtRec_;
    };

    struct ReportVelocityStateData {
      @ext::jaus_presence_vector(16)
      struct ReportVelocityStateRec {
          @optional @range(min=-327.68, max=327.67) @bit_bound(32) @ext::jaus_integer @ext::jaus_integer_function("round") @unit("meter per second") double gPSVelocityDown;

          //! An RMS value indicating the validity of the velocity data.
          @optional @range(min=0.0, max=100.0) @bit_bound(32) @ext::jaus_integer @ext::jaus_integer_function("round") @unit("meter per   second") double velocity_RMS;
          @optional @range(min=-32.768, max=32.767) @bit_bound(16) @ext::jaus_integer @ext::jaus_integer_function("round") @unit("radian per   second") double yawRate;

          //! An RMS value indicating the validity of the rotational velocity data.
          @optional @range(min=0.0, max=3.141592653589793) @bit_bound(16) @ext::jaus_integer @ext::jaus_integer_function("round") @unit("radian per   second") double rate_RMS;

        /// {name="Milliseconds", from_index=0, to_index=9, lower_limit=0, upper_limit=999}
        /// {name="Seconds", from_index=10, to_index=15, lower_limit=0, upper_limit=59}
        /// {name="Minutes", from_index=16, to_index=21, lower_limit=0, upper_limit=59}
        /// {name="Hour", from_index=22, to_index=26, lower_limit=0, upper_limit=23}
        /// {name="Day", from_index=27, to_index=31, lower_limit=1, upper_limit=31}
        //! 
        @optional uint32 timeStamp;
      };

      ReportVelocityStateRec reportVelocityStateRec_;
    };

    struct ReportVelocityStateExtData {
      struct ReportVelocityStateExtSeq {
        struct VelocityVehicleXYZRec {
              @optional @range(min=-327.68, max=327.67) @bit_bound(32) @ext::jaus_integer @ext::jaus_integer_function("round") @unit("meter per second") double gPSVelocityDown;
        };

        struct VelocityLocalXYZRec {
              @optional @range(min=-327.68, max=327.67) @bit_bound(32) @ext::jaus_integer @ext::jaus_integer_function("round") @unit("meter per second") double gPSVelocityDown;
        };

        struct VelocityNEDRec {
              @optional @range(min=-327.68, max=327.67) @bit_bound(32) @ext::jaus_integer @ext::jaus_integer_function("round") @unit("meter per second") double gPSVelocityDown;
        };

        union VelocityVar switch(uint8) {
            case 0: VelocityVehicleXYZRec VelocityVehicleXYZRec_;
            case 1: VelocityLocalXYZRec VelocityLocalXYZRec_;
            case 2: VelocityNEDRec VelocityNEDRec_;
        };

        @ext::jaus_presence_vector(16)
        struct ReportVelocityStateExtRec {

            //! An RMS value indicating the validity of the velocity data.
            @optional @range(min=0.0, max=100.0) @bit_bound(32) @ext::jaus_integer @ext::jaus_integer_function("round") @unit("meter per second") double velocity_RMS;
            @optional @range(min=-32.768, max=32.767) @bit_bound(32) @ext::jaus_integer @ext::jaus_integer_function("round") @unit("radian per   second") double yawRate;

            //! An RMS value indicating the validity of the rotational velocity data.
            @optional @range(min=0.0, max=100.0) @bit_bound(16) @ext::jaus_integer @ext::jaus_integer_function("round") @unit("radian per   second") double rate_RMS;

            //! Scalar speed measured relative to fixed coordinate system
            @optional @range(min=-327.68, max=327.67) @bit_bound(16) @ext::jaus_integer @ext::jaus_integer_function("round") @unit("meter per   second") double speedOverGround;

            //! Scalar speed measured relative to medium, such as air or water currents
            @optional @range(min=-327.68, max=327.67) @bit_bound(16) @ext::jaus_integer @ext::jaus_integer_function("round") @unit("meter per second") double speedRelativeToMedium;
            @optional @range(min=-1000.0, max=1000.0) @bit_bound(16) @ext::jaus_integer @ext::jaus_integer_function("round") @unit("rotations per minute") double rotationsPerMinute;
            @optional @range(min=-327.68, max=327.67) @bit_bound(16) @ext::jaus_integer @ext::jaus_integer_function("round") @unit("meter per   second") double indicatedSpeed;

              //! UTC POSIX-style time in seconds since 1 January 1970
              @unit("second") uint32 gPSFixTimeSeconds;

              //! Nanoseconds component of POSIX-style time
              @unit("one") uint32 gPSFixTimeNanoSeconds;
        };

        VelocityVar velocityVar_;
        ReportVelocityStateExtRec reportVelocityStateExtRec_;
      };

      ReportVelocityStateExtSeq reportVelocityStateExtSeq_;
    };


    @topic(name="QueryVelocityState", qosprofile="jaus_query", id=0x2404)
    //! 
    //! This message shall cause the receiving component to reply to the requestor with a ID 4404h:
    //! ReportVelocityState
    //! (Deprecated) message. A logical AND shall be performed on the requested presence vector and
    //! that representing
    //! the available fields from the responder. The resulting message shall contain the fields
    //! indicated by the result
    //! of this logical AND operation.
    //! 
    struct QueryVelocityState {
      @key JausAddress source;
      JausAddress destination;
      @default(0x2404) int32 id;
      QueryVelocityStateData value;
    };



    @topic(name="QueryVelocityStateExt", qosprofile="jaus_query", id=0x24A4)
    //! 
    //! This message shall cause the receiving component to reply to the requestor with a ID 44A4h:
    //! ReportVelocityStateExt
    //! message. A logical AND shall be performed on the requested presence vector and that
    //! representing the available
    //! fields from the responder. The resulting message shall contain the fields indicated by the
    //! result of this logical
    //! AND operation.
    //! 
    struct QueryVelocityStateExt {
      @key JausAddress source;
      JausAddress destination;
      @default(0x24A4) int32 id;
      QueryVelocityStateExtData value;
    };



    @topic(name="ReportVelocityState", qosprofile="jaus_report", id=0x4404)
    //! 
    //! This message is used to provide the receiver the linear velocity and rotational rate of the
    //! platform.
    //! 
    struct ReportVelocityState {
      @key JausAddress source;
      JausAddress destination;
      @default(0x4404) int32 id;
      ReportVelocityStateData value;
    };



    @topic(name="ReportVelocityStateExt", qosprofile="jaus_report", id=0x44A4)
    @ext::jaus_recommended_query("QueryGlobalLoiter")
    //! 
    //! This message is used to provide the receiver the linear velocity and rotational rate of the
    //! platform. All times are in Coordinated Universal Time (UTC).
    //! 
    struct ReportVelocityStateExt {
      @key JausAddress source;
      JausAddress destination;
      @default(0x44A4) int32 id;
      ReportVelocityStateExtData value;
    };


};
#endif
'''

    global_module = _parser.load(idl_str)
    my_module = global_module.module_by_name('AccelerationStateSensor')

    print (json.dumps(global_module.to_dic(), indent=3))

if __name__ == '__main__':
    test()
